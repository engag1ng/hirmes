"""
Tests for the search pipeline internals.

Covers: RPN conversion (operator precedence, associativity, parentheses),
boolean gates (AND/OR), context window extraction, and make_full_text.

Run: pytest tests/test_search_logic.py -v
"""

import sqlite3
import pytest
from collections import defaultdict

from backend.search import (
    _to_rpn,
    _evaluate_and,
    _evaluate_or,
    _evaluate_not,
    _context_windows,
    make_full_text,
)
from backend.database import initialise_db, get_or_create_doc_id


def _doc_map(*entries):
    """Build a defaultdict doc_map from (path, match_count, total_tf, terms, pages) tuples."""
    m = defaultdict(lambda: {"match_count": 0, "total_tf": 0, "terms": set(), "pages": set()})
    for path, mc, tf, terms, pages in entries:
        m[path] = {"match_count": mc, "total_tf": tf, "terms": set(terms), "pages": set(pages)}
    return m


def _empty_result():
    return defaultdict(lambda: {"match_count": 0, "total_tf": 0, "terms": set(), "pages": set()})


# ── _to_rpn ───────────────────────────────────────────────────────────────────

class TestToRPN:

    def test_single_operand(self):
        assert _to_rpn(["python"]) == ["python"]

    def test_empty_input(self):
        assert _to_rpn([]) == []

    def test_simple_and(self):
        assert _to_rpn(["a", "AND", "b"]) == ["a", "b", "and"]

    def test_simple_or(self):
        assert _to_rpn(["a", "OR", "b"]) == ["a", "b", "or"]

    def test_simple_not(self):
        # NOT is unary prefix; in RPN it comes after its operand
        assert _to_rpn(["NOT", "a"]) == ["a", "not"]

    def test_and_binds_tighter_than_or(self):
        # "a OR b AND c" → AND executes first in RPN
        result = _to_rpn(["a", "OR", "b", "AND", "c"])
        assert result.index("and") < result.index("or"), (
            f"Expected AND before OR in RPN, got: {result}"
        )

    def test_not_binds_tightest(self):
        # "a AND NOT b" → a b NOT AND  (NOT tightest, then AND)
        result = _to_rpn(["a", "AND", "NOT", "b"])
        assert result == ["a", "b", "not", "and"], f"Got: {result}"

    def test_not_right_associative_double_not(self):
        # "NOT NOT a" right-associativity → a not not
        result = _to_rpn(["NOT", "NOT", "a"])
        assert result == ["a", "not", "not"], f"Got: {result}"

    def test_parentheses_override_precedence(self):
        # "(a OR b) AND c" → OR executes first despite lower precedence
        result = _to_rpn(["(", "a", "OR", "b", ")", "AND", "c"])
        assert result.index("or") < result.index("and"), (
            f"Expected OR before AND in RPN (parens override), got: {result}"
        )

    def test_parentheses_stripped_from_output(self):
        result = _to_rpn(["(", "a", "OR", "b", ")"])
        assert "(" not in result
        assert ")" not in result

    def test_complex_nested_precedence_order(self):
        # "(a OR b) AND (c NOT d)" → a b or  c d not  and
        result = _to_rpn(["(", "a", "OR", "b", ")", "AND", "(", "c", "NOT", "d", ")"])
        assert result.index("or") < result.index("not") < result.index("and"), (
            f"Expected or < not < and, got: {result}"
        )

    def test_mismatched_open_paren_raises(self):
        with pytest.raises(ValueError, match="[Mm]ismatched"):
            _to_rpn(["(", "a", "AND", "b"])

    def test_mismatched_close_paren_raises(self):
        with pytest.raises(ValueError, match="[Mm]ismatched"):
            _to_rpn(["a", "AND", "b", ")"])


# ── _evaluate_and ─────────────────────────────────────────────────────────────

class TestEvaluateAnd:

    def test_keeps_only_common_docs(self):
        left  = _doc_map(("/a.txt", 1, 3, {"cat"}, {1}),
                         ("/b.txt", 1, 2, {"cat"}, {2}))
        right = _doc_map(("/b.txt", 1, 5, {"dog"}, {3}),
                         ("/c.txt", 1, 1, {"dog"}, {1}))
        result = _evaluate_and(left, right, _empty_result())
        assert "/a.txt" not in result
        assert "/c.txt" not in result
        assert "/b.txt" in result

    def test_sums_match_count_and_tf(self):
        left  = _doc_map(("/x.txt", 2, 4, {"a"}, {1}))
        right = _doc_map(("/x.txt", 3, 6, {"b"}, {2}))
        result = _evaluate_and(left, right, _empty_result())
        assert result["/x.txt"]["match_count"] == 5
        assert result["/x.txt"]["total_tf"] == 10

    def test_unions_pages(self):
        left  = _doc_map(("/x.txt", 1, 1, {"a"}, {1, 2}))
        right = _doc_map(("/x.txt", 1, 1, {"b"}, {3}))
        result = _evaluate_and(left, right, _empty_result())
        assert result["/x.txt"]["pages"] == {1, 2, 3}

    def test_unions_terms(self):
        left  = _doc_map(("/x.txt", 1, 1, {"cat"}, {1}))
        right = _doc_map(("/x.txt", 1, 1, {"dog"}, {1}))
        result = _evaluate_and(left, right, _empty_result())
        assert result["/x.txt"]["terms"] == {"cat", "dog"}

    def test_empty_intersection_returns_empty(self):
        left  = _doc_map(("/a.txt", 1, 1, {"x"}, {1}))
        right = _doc_map(("/b.txt", 1, 1, {"y"}, {1}))
        result = _evaluate_and(left, right, _empty_result())
        assert len(result) == 0


# ── _evaluate_or ──────────────────────────────────────────────────────────────

class TestEvaluateOr:

    def test_includes_all_docs(self):
        left  = _doc_map(("/a.txt", 1, 1, {"x"}, {1}))
        right = _doc_map(("/b.txt", 1, 1, {"y"}, {1}))
        result = _evaluate_or(left, right, _empty_result())
        assert "/a.txt" in result
        assert "/b.txt" in result

    def test_sums_counts_for_shared_doc(self):
        left  = _doc_map(("/x.txt", 1, 2, {"a"}, {1}))
        right = _doc_map(("/x.txt", 2, 3, {"b"}, {2}))
        result = _evaluate_or(left, right, _empty_result())
        assert result["/x.txt"]["match_count"] == 3
        assert result["/x.txt"]["total_tf"] == 5

    def test_doc_only_in_left_preserved(self):
        left  = _doc_map(("/a.txt", 2, 4, {"x"}, {1}))
        right = _doc_map(("/b.txt", 1, 1, {"y"}, {1}))
        result = _evaluate_or(left, right, _empty_result())
        assert result["/a.txt"]["match_count"] == 2
        assert result["/a.txt"]["total_tf"] == 4

    def test_doc_only_in_right_preserved(self):
        left  = _doc_map(("/a.txt", 1, 1, {"x"}, {1}))
        right = _doc_map(("/b.txt", 3, 9, {"y"}, {2}))
        result = _evaluate_or(left, right, _empty_result())
        assert result["/b.txt"]["match_count"] == 3
        assert result["/b.txt"]["total_tf"] == 9


# ── _evaluate_not ─────────────────────────────────────────────────────────────

class TestEvaluateNot:

    @pytest.fixture
    def db_with_docs(self):
        conn = sqlite3.connect(":memory:")
        initialise_db(conn)
        for path in ["/a.txt", "/b.txt", "/c.txt"]:
            get_or_create_doc_id(conn, path)
        conn.commit()
        return conn

    def test_excludes_operand_docs(self, db_with_docs):
        operand = _doc_map(("/a.txt", 1, 1, {"x"}, {1}))
        result = _evaluate_not(db_with_docs, operand)
        assert "/a.txt" not in result
        assert "/b.txt" in result
        assert "/c.txt" in result

    def test_empty_operand_returns_all(self, db_with_docs):
        result = _evaluate_not(db_with_docs, _empty_result())
        paths = set(result.keys())
        assert {"/a.txt", "/b.txt", "/c.txt"}.issubset(paths)


# ── _context_windows ──────────────────────────────────────────────────────────

class TestContextWindows:

    def test_finds_word_with_surrounding_context(self):
        text = "one two three target four five six"
        results = _context_windows(text, "target", n=2)
        assert len(results) > 0
        assert "target" in results[0].lower()

    def test_absent_word_returns_empty(self):
        assert _context_windows("hello world python", "absent", n=3) == []

    def test_case_insensitive_match(self):
        text = "The Quick Brown FOX jumped"
        results = _context_windows(text, "fox", n=2)
        assert len(results) > 0

    def test_multiple_occurrences_all_returned(self):
        text = "cat sat here and then cat sat there again"
        results = _context_windows(text, "cat", n=1)
        assert len(results) == 2

    def test_n_zero_returns_word_only(self):
        text = "hello target world"
        results = _context_windows(text, "target", n=0)
        assert len(results) > 0
        assert results[0].strip() == "target"

    def test_word_at_start_of_text(self):
        text = "target is the first word here"
        results = _context_windows(text, "target", n=2)
        assert len(results) > 0

    def test_word_at_end_of_text(self):
        text = "the last word is target"
        results = _context_windows(text, "target", n=2)
        assert len(results) > 0


# ── make_full_text ────────────────────────────────────────────────────────────

class TestMakeFullText:

    def test_single_word_unchanged(self):
        assert make_full_text("python") == "python"

    def test_two_words_joined_with_and(self):
        assert make_full_text("python java") == "python AND java"

    def test_three_words(self):
        assert make_full_text("a b c") == "a AND b AND c"

    def test_n_words_has_n_minus_one_ands(self):
        result = make_full_text("a b c d e")
        assert result.count("AND") == 4

    def test_no_trailing_and(self):
        assert not make_full_text("python java rust").endswith("AND")

    def test_no_leading_and(self):
        assert not make_full_text("python java rust").startswith("AND")

    def test_all_words_preserved(self):
        result = make_full_text("indexing retrieval system")
        assert "indexing" in result
        assert "retrieval" in result
        assert "system" in result

    def test_words_and_operators_alternate(self):
        # Every odd-indexed token should be AND
        parts = make_full_text("a b c d").split()
        operators = parts[1::2]
        assert all(op == "AND" for op in operators)
