import os
import datetime
from backend.read import *
from backend.database import *
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
    try:
        initialise_db(conn)
        enable_bulk_mode(conn)
        with conn:
            token_cache = {}
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

                if not is_index:
                    continue

                extractor = match_extractor(new_path)
                pages = extractor(new_path, is_tokenize=True)  # must return list[list[str]]
                doc_id = get_or_create_doc_id(conn, new_path)

                for page_idx, tokens in enumerate(pages, start=1):
                    counts = Counter(tokens)                     # token -> tf (on that page)
                    token_tf_pairs = list(counts.items())
                    bulk_upsert_postings(conn, token_tf_pairs, doc_id, page_idx, _token_cache=token_cache)
    finally:
        disable_bulk_mode(conn)
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
