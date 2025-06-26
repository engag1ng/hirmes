from flask import Flask, render_template, request
from backend.indexer import *
from backend.search import search_index

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html', i=None)

@app.route('/indexing', methods=['POST'])
def indexing():
    path = request.form.get('path')
    recursive = 'recursive' in request.form
    replace_filename = 'replace_filename' in request.form

    i, without_id = get_files_without_id(path, recursive)

    with_id = assign_id(replace_filename, without_id)

    index_files(with_id)

    return render_template('index.html', i=i)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    results = search_index(query)  # You must define this in backend/indexer.py
    return render_template('index.html', i=None, search_results=results)

if __name__ == '__main__':
    app.run(port=5000)