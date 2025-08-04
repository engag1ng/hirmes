from flask import Flask, render_template, request, jsonify
from backend.indexer import *
from backend.search import search_index
import json
import os
import threading
import signal
import sys
from waitress import create_server

app_folder = os.path.join(os.getenv("APPDATA"), "Hirmes")
os.makedirs(app_folder, exist_ok=True)

SETTINGS_FILE = os.path.join(app_folder, "config.json")

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {"recursive": False, "replace_filename": False}

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f)

app = Flask(__name__)
server = None

@app.route('/')
def index_html():
    settings = load_settings()
    return render_template('index.html', settings=settings)

@app.route('/indexing', methods=['POST'])
def api_indexing():
    data = request.json
    path = data.get('path')
    recursive = data.get('recursive', False)
    replace_filename = data.get('replace_filename', False)

    save_settings({
        "recursive": recursive,
        "replace_filename": replace_filename
    })

    i, without_id = get_files_without_id(path, recursive)
    with_id = assign_id(replace_filename, without_id)
    index_files(with_id)

    return jsonify({"indexed_count": i})

@app.route('/search', methods=['GET'])
def api_search():
    query = request.args.get('query')
    try:
        results = search_index(query)
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": "Invalid query format."}), 400

@app.route('/shutdown', methods=["GET"])
def shutdown():
    def shutdown_server():
        print("Shutting down server...")
        server.close()
        sys.exit(0)
    
    threading.Thread(target=shutdown_server).start()
    return jsonify({"message": "Sever is shutting down"}), 200

def run_server():
    global server
    server = create_server(app, host="127.0.0.1", port=5000)
    server.run()
    
if __name__ == '__main__':
    run_server()