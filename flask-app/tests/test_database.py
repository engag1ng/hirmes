"""
Unit tests for backend.database using an in-memory SQLite database.

All tests run against :memory: — no real DB is touched.
Several tests here are EXPECTED TO FAIL on the current code; they document
real bugs that need fixing:

  - test_get_metadata_when_null: json.loads(None) raises TypeError
  - test_update_metadata_when_initially_null: same crash
  - test_delete_cleans_up_postings: orphaned Posting rows are left behind

Run: pytest tests/test_database.py -v
"""

import sqlite3
import pytest

from backend.database import (
    initialise_db,
    get_or_create_doc_id,
    get_metadata_from_doc_id_or_path,
    update_metadata_from_doc_id,
    get_path_from_doc_id,
    bulk_upsert_postings,
    fetch_postings_for_token,
    fetch_all_documents,
    delete_postings_for_doc_id,
    delete_documents,
)


@pytest.fixture
def db():
    """Fresh in-memory SQLite with schema initialised."""
    conn = sqlite3.connect(":memory:")
    initialise_db(conn)
    yield conn
    conn.close()


# ── get_or_create_doc_id ──────────────────────────────────────────────────────

class TestGetOrCreateDocId:

    def test_returns_positive_integer(self, db):
        doc_id = get_or_create_doc_id(db, "/tmp/a.txt")
        assert isinstance(doc_id, int) and doc_id > 0

    def test_same_path_idempotent(self, db):
        id1 = get_or_create_doc_id(db, "/tmp/a.txt")
        id2 = get_or_create_doc_id(db, "/tmp/a.txt")
        assert id1 == id2

    def test_different_paths_different_ids(self, db):
        assert get_or_create_doc_id(db, "/a.txt") != get_or_create_doc_id(db, "/b.txt")

    def test_metadata_stored_when_provided(self, db):
        get_or_create_doc_id(db, "/tmp/a.txt", metadata={"last_indexed": "2024-01-01"})
        meta = get_metadata_from_doc_id_or_path(db, path="/tmp/a.txt")
        assert meta is not None
        assert meta["last_indexed"] == "2024-01-01"

    def test_get_metadata_when_null(self, db):
        """
        BUG: get_or_create_doc_id without metadata stores NULL.
        get_metadata_from_doc_id_or_path then calls json.loads(None) → TypeError.
        Fix: guard with `if row[0] is not None else {}` before json.loads.
        """
        doc_id = get_or_create_doc_id(db, "/tmp/a.txt")   # no metadata → NULL
        meta = get_metadata_from_doc_id_or_path(db, doc_id=doc_id)
        # Should return None (or {}), NOT raise TypeError
        assert meta is None or isinstance(meta, dict)


# ── get_path_from_doc_id ──────────────────────────────────────────────────────

class TestGetPathFromDocId:

    def test_returns_correct_path(self, db):
        doc_id = get_or_create_doc_id(db, "/tmp/z.txt")
        assert get_path_from_doc_id(db, doc_id) == "/tmp/z.txt"

    def test_missing_id_returns_none(self, db):
        assert get_path_from_doc_id(db, 99999) is None


# ── update_metadata_from_doc_id ───────────────────────────────────────────────

class TestUpdateMetadata:

    def test_merge_adds_new_key(self, db):
        doc_id = get_or_create_doc_id(db, "/tmp/a.txt", metadata={"x": 1})
        update_metadata_from_doc_id(db, doc_id, {"y": 2})
        meta = get_metadata_from_doc_id_or_path(db, doc_id=doc_id)
        assert meta["x"] == 1
        assert meta["y"] == 2

    def test_merge_overwrites_existing_key(self, db):
        doc_id = get_or_create_doc_id(db, "/tmp/a.txt", metadata={"x": 1})
        update_metadata_from_doc_id(db, doc_id, {"x": 99})
        meta = get_metadata_from_doc_id_or_path(db, doc_id=doc_id)
        assert meta["x"] == 99

    def test_tags_stored_as_list(self, db):
        doc_id = get_or_create_doc_id(db, "/tmp/a.txt", metadata={})
        update_metadata_from_doc_id(db, doc_id, {"tags": ["finance", "q1"]})
        meta = get_metadata_from_doc_id_or_path(db, doc_id=doc_id)
        assert meta["tags"] == ["finance", "q1"]

    def test_update_metadata_when_initially_null(self, db):
        """
        BUG: when metadata is NULL in the DB (never set), update_metadata_from_doc_id
        calls json.loads(None) → TypeError.
        Fix: treat NULL metadata as an empty dict before merging.
        """
        doc_id = get_or_create_doc_id(db, "/tmp/a.txt")  # NULL metadata
        # Must not raise TypeError
        update_metadata_from_doc_id(db, doc_id, {"key": "value"})
        meta = get_metadata_from_doc_id_or_path(db, doc_id=doc_id)
        assert meta is not None
        assert meta.get("key") == "value"


# ── bulk_upsert_postings ──────────────────────────────────────────────────────

class TestBulkUpsertPostings:

    def test_posting_stored_correctly(self, db):
        doc_id = get_or_create_doc_id(db, "/tmp/a.txt")
        bulk_upsert_postings(db, [("hello", 3)], doc_id, page=1)
        rows = fetch_postings_for_token(db, "hello")
        assert len(rows) == 1
        path, page, tf = rows[0]
        assert path == "/tmp/a.txt"
        assert page == 1
        assert tf == 3

    def test_multiple_tokens_stored(self, db):
        doc_id = get_or_create_doc_id(db, "/tmp/a.txt")
        bulk_upsert_postings(db, [("hello", 2), ("world", 5)], doc_id, page=1)
        assert len(fetch_postings_for_token(db, "hello")) == 1
        assert len(fetch_postings_for_token(db, "world")) == 1

    def test_conflict_accumulates_tf(self, db):
        """On conflict, tf is ADDED (not replaced): 2 + 5 = 7."""
        doc_id = get_or_create_doc_id(db, "/tmp/a.txt")
        bulk_upsert_postings(db, [("word", 2)], doc_id, page=1)
        bulk_upsert_postings(db, [("word", 5)], doc_id, page=1)
        rows = fetch_postings_for_token(db, "word")
        assert rows[0][2] == 7, "tf should accumulate (2+5=7), not replace"

    def test_different_pages_stored_separately(self, db):
        doc_id = get_or_create_doc_id(db, "/tmp/a.txt")
        bulk_upsert_postings(db, [("word", 2)], doc_id, page=1)
        bulk_upsert_postings(db, [("word", 3)], doc_id, page=2)
        rows = fetch_postings_for_token(db, "word")
        assert len(rows) == 2

    def test_token_cache_reused_across_calls(self, db):
        doc_id = get_or_create_doc_id(db, "/tmp/a.txt")
        cache = {}
        bulk_upsert_postings(db, [("shared", 1)], doc_id, page=1, _token_cache=cache)
        bulk_upsert_postings(db, [("shared", 1)], doc_id, page=2, _token_cache=cache)
        assert "shared" in cache


# ── fetch_postings_for_token ──────────────────────────────────────────────────

class TestFetchPostingsForToken:

    def test_unknown_token_returns_empty(self, db):
        assert fetch_postings_for_token(db, "nonexistent") == []

    def test_multiple_docs_for_same_token(self, db):
        d1 = get_or_create_doc_id(db, "/a.txt")
        d2 = get_or_create_doc_id(db, "/b.txt")
        bulk_upsert_postings(db, [("shared", 1)], d1, page=1)
        bulk_upsert_postings(db, [("shared", 4)], d2, page=1)
        rows = fetch_postings_for_token(db, "shared")
        paths = {r[0] for r in rows}
        assert paths == {"/a.txt", "/b.txt"}

    def test_result_format_is_path_page_tf(self, db):
        doc_id = get_or_create_doc_id(db, "/tmp/a.txt")
        bulk_upsert_postings(db, [("term", 7)], doc_id, page=3)
        path, page, tf = fetch_postings_for_token(db, "term")[0]
        assert path == "/tmp/a.txt"
        assert page == 3
        assert tf == 7


# ── fetch_all_documents ───────────────────────────────────────────────────────

class TestFetchAllDocuments:

    def test_empty_db_returns_empty_set(self, db):
        assert fetch_all_documents(db) == set()

    def test_returns_all_indexed_paths(self, db):
        get_or_create_doc_id(db, "/a.txt")
        get_or_create_doc_id(db, "/b.txt")
        docs = fetch_all_documents(db)
        assert "/a.txt" in docs
        assert "/b.txt" in docs

    def test_returns_set_not_list(self, db):
        get_or_create_doc_id(db, "/a.txt")
        assert isinstance(fetch_all_documents(db), set)


# ── delete_documents ──────────────────────────────────────────────────────────

class TestDeleteDocuments:

    def test_document_removed_from_table(self, db):
        get_or_create_doc_id(db, "/tmp/a.txt")
        delete_documents(db, ["/tmp/a.txt"])
        assert "/tmp/a.txt" not in fetch_all_documents(db)

    def test_other_documents_unaffected(self, db):
        get_or_create_doc_id(db, "/tmp/a.txt")
        get_or_create_doc_id(db, "/tmp/b.txt")
        delete_documents(db, ["/tmp/a.txt"])
        assert "/tmp/b.txt" in fetch_all_documents(db)

    def test_empty_list_is_noop(self, db):
        get_or_create_doc_id(db, "/tmp/a.txt")
        delete_documents(db, [])   # must not raise
        assert "/tmp/a.txt" in fetch_all_documents(db)

    def test_delete_cleans_up_postings(self, db):
        """
        BUG: delete_documents only deletes the Document row.
        It does NOT delete associated Posting rows, leaving orphaned data.
        Fix: delete from Posting WHERE doc_id IN (...) before deleting Document.
        """
        doc_id = get_or_create_doc_id(db, "/tmp/a.txt")
        bulk_upsert_postings(db, [("word", 3)], doc_id, page=1)
        delete_documents(db, ["/tmp/a.txt"])
        # Direct query — bypasses the JOIN that hides the orphaned rows
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) FROM Posting WHERE doc_id = ?", (doc_id,))
        orphaned = cur.fetchone()[0]
        assert orphaned == 0, (
            f"delete_documents left {orphaned} orphaned Posting row(s) for deleted doc_id={doc_id}"
        )


# ── delete_postings_for_doc_id ────────────────────────────────────────────────

class TestDeletePostingsForDocId:

    def test_removes_postings(self, db):
        doc_id = get_or_create_doc_id(db, "/tmp/a.txt")
        bulk_upsert_postings(db, [("word", 2)], doc_id, page=1)
        delete_postings_for_doc_id(db, doc_id)
        assert fetch_postings_for_token(db, "word") == []

    def test_does_not_remove_other_docs_postings(self, db):
        d1 = get_or_create_doc_id(db, "/a.txt")
        d2 = get_or_create_doc_id(db, "/b.txt")
        bulk_upsert_postings(db, [("word", 1)], d1, page=1)
        bulk_upsert_postings(db, [("word", 1)], d2, page=1)
        delete_postings_for_doc_id(db, d1)
        rows = fetch_postings_for_token(db, "word")
        assert len(rows) == 1
        assert rows[0][0] == "/b.txt"
