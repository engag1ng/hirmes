import os
import sqlite3
from flask import Blueprint, render_template, request, jsonify
from backend.database import get_metadata_from_doc_id_or_path

bp = Blueprint("tagging", __name__, url_prefix="/tagging")

APP_FOLDER = os.path.join(os.getenv("APPDATA"), "Hirmes")
os.makedirs(APP_FOLDER, exist_ok=True)

DB_PATH = os.path.join(APP_FOLDER, "index.db")

@bp.route("/")
def index():
    return "Welcome to the blog!"

@bp.route("/tags", methods=["POST"])
def get_tags():
    data = request.json
    path = data["path"]
    conn = sqlite3.connect(DB_PATH)
    metadata = get_metadata_from_doc_id_or_path(conn, path=path)
    tags = metadata.get("tags")
    return jsonify({"tag": tags})

@bp.route("/check", methods=["OPTIONS"])
def check():
    if request.method == "OPTIONS":
        return "", 200