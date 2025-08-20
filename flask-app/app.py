"""
Main Flask application file including routes and functions.
"""

import json
import os
import threading
from flask import Flask, render_template, request, jsonify
from waitress import create_server
from backend.indexer import index_path
from backend.search import search_index

APP_FOLDER = os.path.join(os.getenv("APPDATA"), "Hirmes")
os.makedirs(APP_FOLDER, exist_ok=True)

SETTINGS_FILE = os.path.join(APP_FOLDER, "config.json")
server = None # pylint: disable=invalid-name

def _load_settings():
    """Loads settings from SETTINGS_FILE or creates it if it doesn't exist.

    Returns:
        dict: Settings with "name": value format.    
    """

    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding="utf-8") as f:
            return json.load(f)
    return {"recursive": False, "replace_filename": False}

def _save_settings(settings: dict):
    """Saves current settings to SETTINGS_FILE.

    Args:
        settings: In dictionary with "name": value format.
    """

    with open(SETTINGS_FILE, 'w', encoding="utf-8") as f:
        json.dump(settings, f)

app = Flask(__name__)

@app.route('/')
def index_html():
    """Route that renders index.html file.
    """

    settings = _load_settings()
    return render_template('index.html', settings=settings)

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
    replace_filename = data.get('replace_filename', False)

    number_indexed = index_path(path, recursive, replace_filename)

    _save_settings({
        "recursive": recursive,
        "replace_filename": replace_filename
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
    query = data.get('query')
    try:
        results = search_index(query)
        print(results)
        return jsonify({"results": results})
    except Exception: # pylint: disable=broad-exception-caught
        return jsonify({"error": "Invalid query format."}), 400

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

def _run_server():
    """Creates WSGI server at 127.0.0.1:5000 and runs it.

    Returns:
        server: WSGI server object
    """
    serv = create_server(app, host="127.0.0.1", port=5000)
    serv.run()

    return serv

if __name__ == '__main__':
    server = _run_server()
