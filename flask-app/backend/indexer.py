import os
import datetime
from backend.read import *
import sqlite3

app_folder = os.path.join(os.getenv("APPDATA"), "Hirmes")
os.makedirs(app_folder, exist_ok=True)

db_path = os.path.join(app_folder, "index.db")

def fn_index_path(path, is_recursive, is_replace_full):
    i, without_id = get_files_without_id(path, is_recursive)
    index_files(without_id, is_replace_full)

    return i

def index_files(files_tuples, is_replace_full):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for doc_path, is_index in files_tuples:
        ID = datetime.datetime.now().strftime("%y%m%d%H%M%S.%f")
        dir_name = os.path.dirname(doc_path)
        base_name = os.path.basename(doc_path)
        file_name, file_extension = os.path.splitext(base_name)

        if is_replace_full:
            new_name = "★ " + ID + file_extension
        else:
            new_name = file_name + " ★ " + ID + file_extension

        new_path = os.path.join(dir_name, new_name)
        os.rename(doc_path, new_path)

        if is_index:
            extractor_func = match_extractor(new_path)
            pages = extractor_func(new_path, True)

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
                    ''', (token[0], new_path, i + 1, token[1]))

    conn.commit()
    conn.close()


def get_files_without_id(path, is_recursive):
    i = 0
    without_id = []
    
    try:
        objects = os.listdir(path)
    except FileNotFoundError:
        return 0, []

    for file_name in objects:
        full_path = os.path.join(path, file_name)
        if os.path.isdir(full_path) and is_recursive:
            additional_i, additional_without_id = get_files_without_id(full_path, is_recursive)
            i += additional_i
            without_id += additional_without_id
        elif os.path.isfile(full_path):
            if "★" not in file_name:
                if os.stat(full_path).st_size != 0 and match_extractor(full_path) != None:
                    without_id.append((full_path, True))
                else:
                    without_id.append((full_path, False))
                i += 1

    return i, without_id
