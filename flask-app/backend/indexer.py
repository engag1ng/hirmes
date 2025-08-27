"""
Indexing utilities for different file types.

Provides functions for indexing all files in a folder with or without subfolders.

Typical usage:
    from backend.indexer import index_path

    files_indexed = index_files(path, is_recursive=True, is_replace_full=False)
"""

import os
import datetime
import sqlite3
from collections import Counter
from backend.read import match_extractor # pylint: disable=import-error
from backend.database import ( # pylint: disable=import-error
    initialise_db,
    enable_bulk_mode,
    bulk_upsert_postings,
    disable_bulk_mode,
    get_or_create_doc_id
)
from backend.tokenizer import tokenize # pylint: disable=import-error

APP_FOLDER = os.path.join(os.getenv("APPDATA"), "Hirmes")
os.makedirs(APP_FOLDER, exist_ok=True)

DB_PATH = os.path.join(APP_FOLDER, "index.db")

def index_path(path: str, is_recursive: bool, is_replace_full: bool) -> int:
    """Indexes all files in a folder. Can be recursive.

    While indexing files get both renamed with a unique timestamp based ID
    and reverse indexed in an SQLite3 database.

    Args:
        path: String denoting the relative or full path of a folder that should
                be indexed. 
        is_recursive: Boolean indicating if indexing is done recursively.
        is_replace_full: Boolean indicating if full filename will be 
                replaced with ID.

    Returns:
        number_files_found: Integer of how many files got indexed.
    """

    result = _get_files_without_id(path, is_recursive)
    number_files_found = result["number_files_found"]
    files_without_id = result["file_paths"]
    _index_files(files_without_id, is_replace_full)

    return number_files_found

def _get_timestamp():
    """Returns current timestamp.

    The format is YYMMDDHHmmSS.ffffff
    """

    return datetime.datetime.now().strftime("%y%m%d%H%M%S.%f")

def _generate_new_path(file_path: str, is_replace_full: bool) -> str:
    """Generates a new path with timestamp ID.

    Args:
        file_path: String of original file path.
        is_replace_full: Boolean if full name should be replaced.
    Returns:
        new_path: String of new path with timestamp ID.
    """

    directory_name = os.path.dirname(file_path)
    file_name, file_extension = os.path.splitext(os.path.basename(file_path))

    if is_replace_full:
        new_name = "★ " + _get_timestamp() + file_extension
    else:
        new_name = file_name + " ★ " + _get_timestamp() + file_extension

    new_path = os.path.join(directory_name, new_name)

    return new_path

def _index_files(to_index: list, is_replace_full: bool):
    """Renames and indexes all files in to_index.

    Exempt are files with a tuple value like this (path, False).
    These are only renamed and not indexed.

    Args:
        to_index: List of tuples (full_path, is_index)
        is_replace_full: Boolean indicating whether full filename
                is going to be replaced.
    """

    conn = sqlite3.connect(DB_PATH)
    try:
        initialise_db(conn)
        enable_bulk_mode(conn)
        with conn:
            token_cache = {}
            for file_path in to_index:
                new_path = _generate_new_path(file_path, is_replace_full)
                os.rename(file_path, new_path)

                extractor = match_extractor(new_path)
                if not extractor:
                    continue
                content = extractor(new_path)
                if not content:
                    continue
                pages = [tokenize(page) for page in content]
                doc_id = get_or_create_doc_id(conn, new_path)

                for page_idx, tokens in enumerate(pages, start=1):
                    counts = Counter(tokens)                     # token -> tf (on that page)
                    token_tf_pairs = list(counts.items())
                    bulk_upsert_postings(
                        conn,
                        token_tf_pairs,
                        doc_id, page_idx,
                        _token_cache=token_cache
                    )
    finally:
        disable_bulk_mode(conn)
        conn.close()

def _get_files_without_id(path: str, is_recursive: bool) -> dict:
    """Finds all files in path that don't have an ID.

    Can be set to be recursive.

    Args:
        path: String indicating the relative or full path of a folder
        is_recursive: Boolean if files should be found recursively

    Returns:
        dict:
            number_files_found: Integer
            files_paths: Tuple (full path, is_index)
                    is_index denotes whether file should be indexed
                    or just renamed.
    """

    files_found = 0
    without_id = []

    try:
        objects = os.listdir(path)
    except FileNotFoundError:
        return {"number_files_found": files_found, "file_paths": without_id}

    for file_name in objects:
        full_path = os.path.join(path, file_name)
        if os.path.isdir(full_path) and is_recursive:
            recursive_result = _get_files_without_id(full_path, is_recursive)
            files_found += recursive_result["number_files_found"]
            without_id += recursive_result["file_paths"]
        elif os.path.isfile(full_path):
            if "★" not in file_name:
                if os.stat(full_path).st_size != 0 and match_extractor(full_path) is not None:
                    without_id.append(full_path)
                else:
                    without_id.append(full_path)
                files_found += 1

    return {"number_files_found": files_found, "file_paths": without_id}
