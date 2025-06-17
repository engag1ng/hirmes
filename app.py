from flask import Flask, render_template, request
from backend.indexer import *
from backend.search import search_index

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html', data=None)

@app.route('/indexing', methods=['POST'])
def indexing():
    path = request.form.get('path')
    recursive = 'recursive' in request.form
    replace_filename = 'replace_filename' in request.form

    i, without_id = get_files_without_id(path, recursive)
    print(without_id)

    with_id = assign_id(replace_filename, without_id)
    print(with_id)

    index_files(with_id)

    return render_template('index.html', data=i)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query')
    results = search_index(query)  # You must define this in backend/indexer.py
    return render_template('index.html', data=None, search_results=results)

if __name__ == '__main__':
    app.run(debug=True)