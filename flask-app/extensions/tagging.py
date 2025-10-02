"""
Tagging extension for Hirmes.

Allows users to add tags to documents.
"""

import os
import sqlite3
from flask import Blueprint, request, jsonify
from backend.database import get_metadata_from_doc_id_or_path, update_metadata_from_doc_id

bp = Blueprint("tagging", __name__, url_prefix="/tagging")

APP_FOLDER = os.path.join(os.getenv("APPDATA"), "Hirmes")
os.makedirs(APP_FOLDER, exist_ok=True)

DB_PATH = os.path.join(APP_FOLDER, "index.db")

@bp.route("/tags", methods=["POST"])
def get_tags():
    """
    Returns all tags for a path.
    """
    data = request.json
    path = data["path"]
    conn = sqlite3.connect(DB_PATH)
    metadata = get_metadata_from_doc_id_or_path(conn, path=path)
    tags = metadata.get("tags")
    return jsonify({"tag": tags})

@bp.route("/check", methods=["OPTIONS"])
def check():
    """
    Route to check if extension exists.
    """
    return "", 200

@bp.route("/save", methods=["POST"])
def save_tags():
    """
    Save tags for a document to database.
    """
    data = request.json
    path = data["path"]
    tags = data["tags"]

    if not path:
        return jsonify({"error": "Missing 'path'"}), 400
    if not isinstance(tags, list):
        return jsonify({"error": "'tags' must be a list of strings"}), 400

    # ensure everything in list is str
    tags = [str(t) for t in tags]

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT doc_id FROM Document WHERE path = ?", (path,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return jsonify({"error": f"No document found with path {path}"}), 404

    doc_id = row[0]

    update_metadata_from_doc_id(conn, doc_id, {"tags": tags})
    conn.commit()
    conn.close()

    return jsonify({"status": "ok", "path": path, "tags": tags})
