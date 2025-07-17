import os
import datetime
from backend.read import *
import sqlite3

db_path = 'index.db'

def index_files(paths):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for path in paths:
        pages = match_extractor(path)(path, True)

        cur.execute('''
            CREATE TABLE IF NOT EXISTS postings (
                token TEXT,
                path TEXT,
                page INTEGER,
                tf INTEGER
            )
        ''')

        for i, tokens in enumerate(pages):
            for token in tokens:
                cur.execute('''
                    INSERT INTO postings (token, path, page, tf)
                    VALUES (?, ?, ?, ?)
                ''', (token[0], path, i + 1, token[1]))

    conn.commit()
    conn.close()


def get_files_without_id(path, is_recursive):
    i = 0
    without_id = []
    
    try:
        entries = os.listdir(path)
    except FileNotFoundError:
        return 0, []

    for entry in entries:
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path) and is_recursive:
            additional_i, additional_without_id = get_files_without_id(full_path, is_recursive)
            i += additional_i
            without_id += additional_without_id
        elif os.path.isfile(full_path):
            if "★" not in entry:
                without_id.append(full_path)
                i += 1

    return i, without_id

def assign_id(is_replace_full, without_id):
    with_id = []
    for file in without_id:
        ID = datetime.datetime.now().strftime("%y%m%d%H%M%S.%f")
        dir_name = os.path.dirname(file)
        base_name = os.path.basename(file)
        file_name, file_extension = os.path.splitext(base_name)

        if is_replace_full:
            new_name = "★ " + ID + file_extension
        else:
            new_name = file_name + " ★ " + ID + file_extension

        new_path = os.path.join(dir_name, new_name)
        os.rename(file, new_path)
        with_id.append(new_path)
        
    return with_id