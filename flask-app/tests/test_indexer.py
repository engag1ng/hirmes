"""
Integration tests for the indexing pipeline.

Uses tmp_path for real files and monkeypatches backend.indexer.DB_PATH to
avoid touching the user's real database.

Run: pytest tests/test_indexer.py -v
"""

import sqlite3
import pytest
from backend.database import initialise_db, fetch_all_documents, fetch_postings_for_token
from backend.indexer import index_path


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point the indexer at a fresh temp database."""
    db_file = str(tmp_path / "test.db")
    monkeypatch.setattr("backend.indexer.DB_PATH", db_file)
    conn = sqlite3.connect(db_file)
    initialise_db(conn)
    conn.commit()
    conn.close()
    return db_file


@pytest.fixture
def text_files(tmp_path):
    """Two .txt files in root, one in a subdirectory."""
    (tmp_path / "a.txt").write_text("the quick brown fox jumps over the lazy dog")
    (tmp_path / "b.txt").write_text("information retrieval systems are very useful")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.txt").write_text("nested file content for recursive indexing test")
    return tmp_path


# ── index_path return value ───────────────────────────────────────────────────

class TestIndexPathCount:

    def test_non_recursive_counts_root_files_only(self, temp_db, text_files):
        count = index_path(str(text_files), is_recursive=False)
        assert count == 2  # a.txt + b.txt; sub/c.txt excluded

    def test_recursive_counts_all_files(self, temp_db, text_files):
        count = index_path(str(text_files), is_recursive=True)
        assert count == 3  # a.txt + b.txt + sub/c.txt

    def test_nonexistent_path_returns_zero(self, temp_db):
        assert index_path("/nonexistent/path/xyz", is_recursive=False) == 0

    def test_already_indexed_files_not_counted_again(self, temp_db, text_files):
        index_path(str(text_files), is_recursive=False)
        second = index_path(str(text_files), is_recursive=False)
        assert second == 0  # nothing new to index


# ── database state after indexing ─────────────────────────────────────────────

class TestIndexPathDatabase:

    def test_root_files_appear_in_db(self, temp_db, text_files):
        index_path(str(text_files), is_recursive=False)
        conn = sqlite3.connect(temp_db)
        docs = fetch_all_documents(conn)
        conn.close()
        assert any("a.txt" in p for p in docs)
        assert any("b.txt" in p for p in docs)

    def test_non_recursive_excludes_subdirectory(self, temp_db, text_files):
        index_path(str(text_files), is_recursive=False)
        conn = sqlite3.connect(temp_db)
        docs = fetch_all_documents(conn)
        conn.close()
        assert not any("c.txt" in p for p in docs)

    def test_recursive_includes_subdirectory(self, temp_db, text_files):
        index_path(str(text_files), is_recursive=True)
        conn = sqlite3.connect(temp_db)
        docs = fetch_all_documents(conn)
        conn.close()
        assert any("c.txt" in p for p in docs)

    def test_tokens_written_to_posting_table(self, temp_db, text_files):
        index_path(str(text_files), is_recursive=False)
        conn = sqlite3.connect(temp_db)
        # "fox" is not a stop word; should appear in postings
        rows = fetch_postings_for_token(conn, "fox")
        conn.close()
        assert len(rows) >= 1

    def test_empty_directory_indexes_nothing(self, temp_db, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.indexer.DB_PATH", temp_db)
        empty = tmp_path / "empty"
        empty.mkdir()
        count = index_path(str(empty), is_recursive=False)
        assert count == 0
        conn = sqlite3.connect(temp_db)
        docs = fetch_all_documents(conn)
        conn.close()
        assert len(docs) == 0

    def test_unsupported_extension_not_indexed(self, temp_db, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.indexer.DB_PATH", temp_db)
        (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n")
        (tmp_path / "note.txt").write_text("indexable content here")
        index_path(str(tmp_path), is_recursive=False)
        conn = sqlite3.connect(temp_db)
        docs = fetch_all_documents(conn)
        conn.close()
        # .png is not supported; .txt is
        # Both end up in the file_paths list (current behavior) but only .txt gets postings
        txt_rows = fetch_postings_for_token(conn, "indexable")
        assert not any("image.png" in p for p in docs if p.endswith(".png"))


# ── progress callback ─────────────────────────────────────────────────────────

class TestProgressCallback:

    def test_callback_call_count(self, temp_db, text_files):
        """Expect 1 initial call (0/total) + 1 per file = total+1 calls."""
        calls = []
        index_path(str(text_files), is_recursive=False, progress_callback=calls.append)
        # 2 files → 3 calls: (0,2), (1,2), (2,2)
        assert len(calls) == 3

    def test_callback_starts_at_zero(self, temp_db, text_files):
        calls = []
        index_path(str(text_files), is_recursive=False, progress_callback=calls.append)
        current, total = calls[0]
        assert current == 0
        assert total == 2

    def test_callback_ends_at_total(self, temp_db, text_files):
        calls = []
        index_path(str(text_files), is_recursive=False, progress_callback=calls.append)
        current, total = calls[-1]
        assert current == total == 2

    def test_callback_current_is_monotonic(self, temp_db, text_files):
        currents = []

        def cb(current, total):
            currents.append(current)

        index_path(str(text_files), is_recursive=False, progress_callback=cb)
        assert currents == sorted(currents)

    def test_callback_total_is_constant(self, temp_db, text_files):
        totals = []

        def cb(current, total):
            totals.append(total)

        index_path(str(text_files), is_recursive=False, progress_callback=cb)
        assert len(set(totals)) == 1, f"total changed across calls: {totals}"

    def test_no_callback_does_not_raise(self, temp_db, text_files):
        count = index_path(str(text_files), is_recursive=False, progress_callback=None)
        assert count == 2
