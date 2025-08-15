import sqlite3
import json
from collections import Counter

def initialise_db(conn):
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS Document (
    doc_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    path     TEXT UNIQUE NOT NULL,
    metadata TEXT
    );

    CREATE TABLE IF NOT EXISTS Token (
    token_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    token_text TEXT UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS Posting (
    token_id INTEGER NOT NULL,
    doc_id   INTEGER NOT NULL,
    page     INTEGER NOT NULL,
    tf       INTEGER NOT NULL,
    PRIMARY KEY (token_id, doc_id, page),
    FOREIGN KEY (token_id) REFERENCES Token(token_id),
    FOREIGN KEY (doc_id)   REFERENCES Document(doc_id)
    );

    CREATE INDEX IF NOT EXISTS idx_posting_token   ON Posting(token_id);
    CREATE INDEX IF NOT EXISTS idx_posting_doc     ON Posting(doc_id);
    CREATE INDEX IF NOT EXISTS idx_token_text      ON Token(token_text);
    """)

def get_doc_id_from_path(conn, path):
    cur = conn.cursor()
    cur.execute("SELECT doc_id FROM Document WHERE path = ?", (path,))
    row = cur.fetchone()
    return row[0] if row else None

def get_or_create_doc_id(conn, path, metadata=None):
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO Document(path, metadata) VALUES(?, ?)",
                (path, json.dumps(metadata) if metadata is not None else None))
    cur.execute("SELECT doc_id FROM Document WHERE path = ?", (path,))
    return cur.fetchone()[0]

def get_path_from_doc_id(conn, doc_id):
    cur = conn.cursor()
    cur.execute("SELECT path FROM Document WHERE doc_id = ?", (doc_id,))
    row = cur.fetchone()
    return row[0] if row else None

def _ensure_token_ids(conn, tokens, cache):
    """
    Given an iterable of token_text, ensure they exist in Token and
    return a dict token_text -> token_id. Uses/updates `cache` (dict).
    """
    to_insert = [t for t in tokens if t not in cache]
    if to_insert:
        cur = conn.cursor()
        # bulk insert ignore
        cur.executemany("INSERT OR IGNORE INTO Token(token_text) VALUES(?)",
                        ((t,) for t in to_insert))
        # bulk fetch ids for all new tokens
        # Build a dynamic IN (...) clause safely
        placeholders = ",".join("?" for _ in to_insert)
        cur.execute(f"SELECT token_id, token_text FROM Token WHERE token_text IN ({placeholders})",
                    to_insert)
        for tid, ttext in cur.fetchall():
            cache[ttext] = tid
    return cache

def bulk_upsert_postings(conn, token_tf_pairs, doc_id, page, _token_cache=None):
    """
    token_tf_pairs: iterable[(token_text, tf)]
    Upserts rows in Posting with tf aggregation.
    """
    if _token_cache is None:
        _token_cache = {}

    tokens = [t for t, _ in token_tf_pairs]
    _ensure_token_ids(conn, tokens, _token_cache)

    rows = []
    for token_text, tf in token_tf_pairs:
        token_id = _token_cache[token_text]
        rows.append((token_id, doc_id, page, int(tf)))

    cur = conn.cursor()
    cur.executemany("""
        INSERT INTO Posting(token_id, doc_id, page, tf)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(token_id, doc_id, page)
        DO UPDATE SET tf = Posting.tf + excluded.tf
    """, rows)

def fetch_postings_for_token(conn, token_text):
    """
    Returns list of (path, page, tf) for a given token_text.
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT d.path, p.page, p.tf
        FROM Posting p
        JOIN Token t ON t.token_id = p.token_id
        JOIN Document d ON d.doc_id = p.doc_id
        WHERE t.token_text = ?
    """, (token_text,))
    return cur.fetchall()

def enable_bulk_mode(conn):
    cur = conn.cursor()
    cur.executescript("""
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = OFF;
        PRAGMA temp_store = MEMORY;
        PRAGMA cache_size = -200000; -- ~200k pages in memory
    """)

def disable_bulk_mode(conn):
    cur = conn.cursor()
    cur.executescript("""
        PRAGMA synchronous = NORMAL;
    """)

def _term_doc_map(conn, token):
    # returns {(path, page): {"match_count": 1, "total_tf": tf, "terms": {token}}}
    rows = fetch_postings_for_token(conn, token)
    m = {}
    for path, page, tf in rows:
        key = (path, page)
        m[key] = {"match_count": 1, "total_tf": tf, "terms": {token}}
    return m