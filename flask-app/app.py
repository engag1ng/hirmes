"""
Main Flask application file including routes and functions.
"""

import json
import os
import threading
from flask import Flask, render_template, request, jsonify, redirect, url_for
from waitress import create_server
from backend.indexer import index_path
from backend.search import search_index, make_full_text
from backend.watchdog import run_watchdog
from backend.settings import load_settings, save_settings

from blueprints.tagging import bp as tagging_bp

APP_FOLDER = os.path.join(os.getenv("APPDATA"), "Hirmes")
os.makedirs(APP_FOLDER, exist_ok=True)

server = None # pylint: disable=invalid-name


app = Flask(__name__)
app.register_blueprint(tagging_bp)

@app.route('/')
def index_html():
    """Route that renders index.html file.
    """

    settings = load_settings()
    
    num_files_reindexed, num_files_deleted, num_files_indexed = (
        run_watchdog(settings["watchdog_number"])
    )

    return render_template('index.html', settings=settings)

@app.route('/open-file', methods=['POST'])
def open_file():
    data = request.get_json(force=True)
    filename = data.get('path')
    if not filename:
        return jsonify(error='No path provided'), 400

    file_path = os.path.abspath(filename)

    if not os.path.isfile(file_path):
        return jsonify(error='File not found'), 404

    try:
        os.startfile(file_path)
    except Exception as e:
        return jsonify(error=str(e)), 500

    return jsonify(status='ok', file=file_path), 200

@app.route('/settings')
def settings_html():
    """Route that renders settings menu
    """

    settings = load_settings()
    return render_template('settings.html', settings=settings)

@app.route('/settings/save', methods=['POST'])
def api_save_settings():
    """Route for saving settings.
    """

    save_settings({
        "watchdog_number": request.form.get('watchdog_number'),
    })

    return redirect(url_for("settings_html"))

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

    number_indexed = index_path(path, recursive)

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
