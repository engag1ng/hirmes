"""
Utilities for reindexing documents regularly

Typical usage:
    run_watchdog(50) # Reindexes 50 files
"""

import sqlite3
import json
import os
from backend.indexer import repeat_indexing, index_path
from backend.settings import load_settings
from backend.database import initialise_db

APP_FOLDER = os.path.join(os.getenv("APPDATA"), "Hirmes")
os.makedirs(APP_FOLDER, exist_ok=True)

DB_PATH = os.path.join(APP_FOLDER, "index.db")

WATCHDOG_PATH = os.path.join(APP_FOLDER, "watchdog.txt")

def run_watchdog(n: int) -> tuple[int]:
    """Reindexes n files.

    Args:
        n: Integer of files to reindex.

    Returns:
        (int, int, int): Files reindexed, deleted, newly indexed
    """
    conn = sqlite3.connect(DB_PATH)
    initialise_db(conn)
    to_index = _find_files_to_reindex(conn, n)
    number_reindexed, number_deleted = repeat_indexing(conn, to_index)
    number_files_indexed = _check_watchdog_list()
    conn.commit()
    conn.close()

    return number_reindexed, number_deleted, number_files_indexed

def _find_files_to_reindex(conn, n: int) -> list[str]:
    """Finds n files that haven't been indexed in the past two weeks

    Args:
        conn: SQLite3 connection object.
        n: Number of files to find.

    Returns:
        results: List of paths to documents.
    """

    cursor = conn.cursor()
    cursor.execute("""
        SELECT path
        FROM Document
        WHERE 
            metadata IS NULL
            OR json_extract(metadata, '$.last_indexed') IS NULL
            OR datetime(json_extract(metadata, '$.last_indexed')) <= datetime('now', '-14 days')
        ORDER BY datetime(json_extract(metadata, '$.last_indexed')) ASC
        LIMIT ?;
    """, (n,))
    results = cursor.fetchall()

    return [row[0] for row in results]

def _check_watchdog_list() -> int:
    """Checks all paths in the watchdog list for new files to index.

    Also indexes them.

    Returns:
        number_files_indexed: Integer
    """
    number_files_indexed = 0
    settings = load_settings()
    is_recursive = settings["recursive"]
    is_replace_full = False
    try:
        open(WATCHDOG_PATH, 'x')
    except FileExistsError:
        with open(WATCHDOG_PATH, 'r', encoding="UTF-8") as file:
            content = file.readlines()
        for path in content:
            number_files_indexed += index_path(path, is_recursive, is_replace_full)

    return number_files_indexed