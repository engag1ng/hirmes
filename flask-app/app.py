"""
Main Flask application file including routes and functions.
"""

import os
import sys
import sqlite3
import subprocess
import threading
import importlib
import pkgutil
from flask import Flask, render_template, request, jsonify, redirect, url_for
from waitress import create_server
from backend.indexer import index_path
from backend.search import search_index, make_full_text
from backend.watchdog import run_watchdog
from backend.settings import load_settings, save_settings, APP_FOLDER
from backend.database import get_metadata_from_doc_id_or_path, update_metadata_from_doc_id

WATCHDOG_FILE = os.path.join(APP_FOLDER, "watchdog.txt")
DB_PATH = os.path.join(APP_FOLDER, "index.db")

server = None # pylint: disable=invalid-name

_progress_lock = threading.Lock()
_progress = {"current": 0, "total": 0}

app = Flask(__name__)

@app.route('/')
def index_html():
    """Route that renders index.html file.
    """

    settings = load_settings()

    run_watchdog(settings["watchdog_number"])

    return render_template('index.html', settings=settings)

@app.route('/open-file', methods=['POST'])
def open_file():
    """
    Uses OS to open a file on the users computer.
    """
    data = request.get_json(force=True)
    filename = data.get('path')
    if not filename:
        return jsonify(error='No path provided'), 400

    file_path = os.path.abspath(filename)

    if not os.path.isfile(file_path):
        return jsonify(error='File not found'), 404

    try:
        if sys.platform == "win32":
            os.startfile(file_path)
        else:
            subprocess.Popen(["xdg-open", file_path])
    except Exception as e:
        return jsonify(error=str(e)), 500

    return jsonify(status='ok', file=file_path), 200

@app.route('/settings')
def settings_html():
    """Route that renders settings menu
    """

    settings = load_settings()
    if os.path.exists(WATCHDOG_FILE):
        with open(WATCHDOG_FILE, 'r', encoding="utf-8") as f:
            watchdog_list = ''.join(f.readlines())
    else:
        watchdog_list = ""
    return render_template(
        'settings.html',
        settings=settings,
        watchdog_list=watchdog_list,
        extensions=discover_extensions()
    )

@app.route('/settings/save', methods=['POST'])
def api_save_settings():
    """Route for saving settings.
    """
    watchdog_number = request.form.get('watchdog_number')
    watchdog_list = request.form.get('watchdog_list')
    enabled_extensions = request.form.getlist('extensions')  # multiple select!

    save_settings({
        "watchdog_number": watchdog_number,
        "enabled_extensions": enabled_extensions,
    })

    with open(WATCHDOG_FILE, 'w', encoding="utf-8") as f:
        f.write(watchdog_list or "")

    return redirect(url_for("settings_html"))

@app.route('/progress', methods=['GET'])
def api_progress():
    """Returns current indexing progress.

    Returns:
        json: JSON object:
            "current": Files processed so far.
            "total": Total files to index (0 while scanning).
    """
    with _progress_lock:
        return jsonify(dict(_progress))

@app.route('/indexing', methods=['POST'])
def api_indexing():
    """Route for indexing files.

    Returns:
        json: JSON object:
            "indexed_count": Number of files indexed.
    """

    data = request.get_json(force=True)
    path = data.get('path')
    recursive = data.get('recursive', False)

    with _progress_lock:
        _progress["current"] = 0
        _progress["total"] = 0

    def on_progress(current, total):
        with _progress_lock:
            _progress["current"] = current
            _progress["total"] = total

    number_indexed = index_path(path, recursive, on_progress)

    save_settings({
        "recursive": recursive,
    })

    return jsonify({"indexed_count": number_indexed})

@app.route('/search', methods=['POST'])
def api_search():
    """Route for searching database.

    Returns:
        JSON object:
            "results": Results from search_index(query)
            "error": "Invalid query format.", 400
    """

    data = request.get_json(force=True)
    full_text = data.get('full_text', False)
    query = data.get('query')
    if full_text:
        query = make_full_text(query)
    try:
        results, spellchecked = search_index(query)
        return jsonify({"results": results, "spellchecked": spellchecked})
    except Exception: # pylint: disable=broad-exception-caught
        return jsonify({"error": "An error occurred. Check query format."}), 400

@app.route('/shutdown', methods=["GET"])
def shutdown():
    """Route for shutting down server.

    Returns:
        JSON object:
            "message": "Server is shutting down", 200
    """

    def shutdown_server():
        """Function to shut down server.
        """
        print("Shutting down server...")
        server.close()
        os._exit(0)

    threading.Thread(target=shutdown_server).start()
    return jsonify({"message": "Sever is shutting down"}), 200

@app.route('/tagging/tags', methods=['POST'])
def tagging_get_tags():
    """Returns all tags for a given file path."""
    data = request.get_json(force=True)
    path = data["path"]
    conn = sqlite3.connect(DB_PATH)
    metadata = get_metadata_from_doc_id_or_path(conn, path=path)
    conn.close()
    if not metadata:
        return jsonify({"tag": "Error fetching tags"})
    return jsonify({"tag": metadata.get("tags")})

@app.route('/tagging/save', methods=['POST'])
def tagging_save_tags():
    """Saves tags for a document to the database."""
    data = request.get_json(force=True)
    path = data["path"]
    tags = data["tags"]
    if not path:
        return jsonify({"error": "Missing 'path'"}), 400
    if not isinstance(tags, list):
        return jsonify({"error": "'tags' must be a list of strings"}), 400
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

def discover_extensions():
    """Find and import all modules in a package that define a 'blueprint'."""
    package_name = "extensions"
    package = importlib.import_module(package_name)
    discovered = []

    for _, module_name, ispkg in pkgutil.iter_modules(package.__path__):
        if ispkg:
            continue
        full_module_name = f"{package_name}.{module_name}"
        module = importlib.import_module(full_module_name)

        if hasattr(module, "bp"):
            discovered.append((module_name, module.bp))

    return discovered

def _run_server():
    """Creates WSGI server at 127.0.0.1:5000 and runs it.

    Returns:
        server: WSGI server object
    """
    serv = create_server(app, host="127.0.0.1", port=5000)
    serv.run()

    return serv

if __name__ == '__main__':
    extensions = load_settings()["enabled_extensions"]
    for name, bp in discover_extensions():
        if name in extensions:
            app.register_blueprint(bp, url_prefix=f"/{name}")

    server = _run_server()
