from flask import Flask, render_template, request
from backend.indexer import *
from backend.search import search_index
import webbrowser
import json
import os
from random import randint

SETTINGS_FILE = 'config.json'

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {"recursive": False, "replace_filename": False}

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f)

def render_index_html(i=None):
    if randint(1, 5) == 5:
        check_file_status()
    settings = load_settings()
    return render_template('index.html', i=i, settings=settings)

app = Flask(__name__)

@app.route('/')
def index_html():
    return render_index_html()

@app.route('/indexing', methods=['POST'])
def indexing():
    path = request.form.get('path')
    recursive = 'recursive' in request.form
    replace_filename = 'replace_filename' in request.form

    save_settings({
        "recursive": recursive,
        "replace_filename": replace_filename
    })

    i, without_id = get_files_without_id(path, recursive)
    with_id = assign_id(replace_filename, without_id)
    index_files(with_id)

    return render_index(i=i)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    results = search_index(query)  # You must define this in backend/indexer.py
    return render_template('index.html', i=None, search_results=results)

if __name__ == '__main__':
    webbrowser.open("http://127.0.0.1:5000")
    app.run(port=5000)