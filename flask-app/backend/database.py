"""
Database utilities for managing index.

Functions for CRUD operations on all tables.

Typical usage:
    from backend.database import initialise database

    initialise_db(conn)
    doc_id = get_or_create_doc_id(conn, path)
    bulk_upsert_postings(conn, token_tf_pairs, doc_id, page)
    fetch_postings_for_token(conn, token_text)
"""

import json

def initialise_db(conn):
    """Creates all necessary tables and indeces in the database.

    Args:
        conn: SQLite3 Connection object
    """

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

def get_or_create_doc_id(conn, path: str, metadata=None) -> int:
    """Creates and/or retrieves doc_id for path from Document table.

    If a doc_id already exists for the path then it is returned. 
    If it doesn't exist it is first created and then returned. 

    Args:
        conn: SQLite3 connection object
        path: String denoting the full path of a file
        metadata: Additional metadata to append to the entry
    
    Returns:
        doc_id: As integer
    """

    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO Document(path, metadata) VALUES(?, ?)",
                (path, json.dumps(metadata) if metadata is not None else None))
    cur.execute("SELECT doc_id FROM Document WHERE path = ?", (path,))
    row = cur.fetchone()
    doc_id = row[0]

    return doc_id

def get_metadata_from_doc_id(conn, doc_id: int) -> dict | None:
    """Returns the metadata associated with the doc_id.

    Args:
        conn: SQLite3 connection object
        doc_id: Integer document identifier

    Returns:
        metadata: Dictionary format
        None: If no metadata exists
    """

    cur = conn.cursor()
    cur.execute("SELECT metadata FROM Document WHERE doc_id = ?", (doc_id,))
    row = cur.fetchone()
    if row:
        data = json.loads(row[0])
        return data
    else:
        return None

def update_metadata_from_doc_id(conn, doc_id: int, updates: dict):
    """
    Updates the metadata for a certain doc_id

    Args:
        conn: SQLite3 connection object
        doc_id: Int Document indentifier
        updates: Dict with key: value updates
    """
    cur = conn.cursor()
    cur.execute("SELECT metadata FROM Document WHERE doc_id = ?", (doc_id,))
    row = cur.fetchone()

    if not row:
        return

    metadata = json.loads(row[0])
    metadata.update(updates)

    cur.execute(
        "UPDATE Document SET metadata = ? WHERE doc_id = ?",
        (json.dumps(metadata), doc_id)
    )

def get_path_from_doc_id(conn, doc_id: int) -> str | None:
    """Retrieves path for doc_id from Document table.

    Args:
        conn: SQLite3 connection object
        doc_id: Integer denoting the ID of a file

    Returns:
        path: String denoting the full path to a file
        None: If doc_id doesn't exist in database
    """

    cur = conn.cursor()
    cur.execute("SELECT path FROM Document WHERE doc_id = ?", (doc_id,))
    row = cur.fetchone()
    path = row[0] if row else None

    return path

def _ensure_token_ids(conn, tokens: list[str], cache: dict) -> dict:
    """
    Ensure token_text's exist in Token and return a dict token_text -> token_id.
    Uses/updates `cache` (dict).

    Args:
        conn: SQLite3 connection object
        tokens: List of tokens in string format

    Returns:
        cache: A dictionary of token_text: token_id
    """

    to_insert = [t for t in tokens if t not in cache]
    if to_insert:
        cur = conn.cursor()
        cur.executemany("INSERT OR IGNORE INTO Token(token_text) VALUES(?)",
                        ((t,) for t in to_insert))
        placeholders = ",".join("?" for _ in to_insert)
        cur.execute(f"SELECT token_id, token_text FROM Token WHERE token_text IN ({placeholders})",
                    to_insert)
        for tid, ttext in cur.fetchall():
            cache[ttext] = tid

    return cache

def bulk_upsert_postings(
    conn,token_tf_pairs: list[tuple], doc_id: int, page: int, _token_cache=None
):
    """Inserts many Tokens for a doc_id into Posting table

    Also creates a cache if None exists. 

    Args:
        conn: SQLite3 connection object
        token_tf_pairs: List of tuples representing token_text and term_frequency pairs
        doc_id: Integer ID of file that tokens belong to
        page: Integer page indicator for files that support page-by-page indexing (else 1)
        _token_cache (optional): Dictionary representing token_text: token_id pairs
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

def fetch_postings_for_token(conn, token_text: str) -> list[tuple]:
    """Returns list of (path, page, tf) for a given token_text.

    Args:
        conn: SQLite3 connection object
        token_text: String token

    Returns:
        rows: List of (path, page, tf) for a given token_text.
    """

    cur = conn.cursor()
    cur.execute("""
        SELECT d.path, p.page, p.tf
        FROM Posting p
        JOIN Token t ON t.token_id = p.token_id
        JOIN Document d ON d.doc_id = p.doc_id
        WHERE t.token_text = ?
    """, (token_text,))
    rows = cur.fetchall()

    return rows

def enable_bulk_mode(conn):
    """Turns on optional SQLite3 settings to enable for fast bulk insert.

    Args:
        conn: SQLite3 connection object
    """

    cur = conn.cursor()
    cur.executescript("""
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = OFF;
        PRAGMA temp_store = MEMORY;
        PRAGMA cache_size = -200000; -- ~200k pages in memory
    """)

def disable_bulk_mode(conn):
    """Sets PRAGMA synchronous to NORMAL mode.

    Args:
        conn: SQLite3 connection object
    """

    cur = conn.cursor()
    cur.executescript("""
        PRAGMA synchronous = NORMAL;
    """)

def _term_doc_map(conn, token: str) -> dict:
    """Returns a dictionary mapping of path, page to important information.

    The returned dictionary is a mapping of (path, page) to a dictionary of 
    {"match_count": 1, "total_tf": term frequency, "terms" {token}}.

    Args:
        conn: SQLite3 connection object
        token: String token
    """
    rows = fetch_postings_for_token(conn, token)
    m = {}
    for path, page, tf in rows:
        key = (path, page)
        m[key] = {"match_count": 1, "total_tf": tf, "terms": {token}}

    return m

def fetch_all_documents(conn) -> set:
    """
    Fetch all document IDs in the collection.

    Args:
        conn: SQLite3 connection object.

    Returns:
        set of doc_ids
    """
    cursor = conn.cursor()
    cursor.execute("SELECT path FROM Document")
    result = {row[0] for row in cursor.fetchall()}

    return result

def delete_postings_for_doc_id(conn, doc_id: int):
    """Deletes all postings for doc_id.

    Args:
        conn: SQLite3 connection object
        doc_id: Integer document indentifier
    """

    cur = conn.cursor()
    cur.execute("""
        DELETE FROM Posting
        WHERE doc_id = ?
    """, (doc_id,))

def delete_documents(conn, to_delete: list):
    """Deletes all Documents from to_delete.

    Args:
        conn: SQLite3 connection object
        to_delete: List of paths to documents.
    """

    if not to_delete:  # nothing to delete
        return

    cur = conn.cursor()
    placeholders = ",".join("?" * len(to_delete))
    query = f"DELETE FROM Document WHERE path IN ({placeholders})"
    cur.execute(query, tuple(to_delete))
    conn.commit()
