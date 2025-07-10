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

def render_index_html(i=None, search_results=None):
    settings = load_settings()
    return render_template('index.html', i=i, search_results=search_results, settings=settings)

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

    return render_index_html(i=i)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    results = search_index(query)
    return render_index_html(search_results=results)
    
if __name__ == '__main__':
    from waitress import serve
    serve(app, host='127.0.0.1', port=5000)