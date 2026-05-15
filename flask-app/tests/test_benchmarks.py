"""
Benchmarks using pytest-benchmark.

Run:  pytest tests/test_benchmarks.py -v --benchmark-sort=mean
Save: pytest tests/test_benchmarks.py --benchmark-save=baseline
Compare: pytest tests/test_benchmarks.py --benchmark-compare=baseline

Each benchmark is a tight, isolated measurement — no I/O, no real DB queries
except where explicitly noted. Use these as a regression baseline; a 2×
slowdown on any benchmark is worth investigating before merging.
"""

import sqlite3
import pytest

from backend.tokenizer import tokenize, tokenize_query
from backend.search import _to_rpn, make_full_text, _evaluate_and, _evaluate_or
from backend.database import (
    initialise_db,
    get_or_create_doc_id,
    bulk_upsert_postings,
    fetch_postings_for_token,
)

# ── Shared test data ───────────────────────────────────────────────────────────

_SHORT_TEXT = "information retrieval system for indexing documents"

_LONG_TEXT = (
    "Information retrieval is the activity of obtaining information resources "
    "relevant to an information need from a collection. Searches can be based "
    "on full-text or other content-based indexing. Automated IR systems are "
    "used to reduce information overload. Documents are stored in an inverted "
    "index that maps tokens to document identifiers and term frequencies. "
    "Boolean queries combine search terms with AND OR and NOT operators. "
    "Ranked retrieval systems sort results by relevance scores computed from "
    "term frequency and inverse document frequency measures. "
) * 30  # ~3 000 words

_SIMPLE_TOKENS = ["python", "AND", "java"]
_COMPLEX_TOKENS = [
    "(", "retrieval", "OR", "indexing", ")", "AND", "NOT",
    "database", "AND", "(", "python", "OR", "java", ")", "NOT", "web"
]


def _large_posting_list(n, offset=0):
    return [
        {"doc_id": i + offset, "match_count": 1, "total_tf": i + 1,
         "terms": {"term"}, "pages": {1}}
        for i in range(n)
    ]


# ── Tokenizer ─────────────────────────────────────────────────────────────────

def test_bench_tokenize_short(benchmark):
    """Single sentence — baseline for per-call overhead."""
    benchmark(tokenize, _SHORT_TEXT)


def test_bench_tokenize_long(benchmark):
    """~3 000-word document — reveals scaling behaviour."""
    benchmark(tokenize, _LONG_TEXT)


def test_bench_tokenize_query_simple(benchmark):
    """Three-token query."""
    benchmark(tokenize_query, "python AND java")


def test_bench_tokenize_query_complex(benchmark):
    """Multi-operator query with parentheses."""
    benchmark(tokenize_query, "( retrieval OR indexing ) AND NOT database AND ( python OR java )")


# ── make_full_text ────────────────────────────────────────────────────────────

def test_bench_make_full_text_10(benchmark):
    """10-word phrase → 19-token AND query."""
    phrase = "one two three four five six seven eight nine ten"
    benchmark(make_full_text, phrase)


def test_bench_make_full_text_100(benchmark):
    """100-word phrase — exercises list join loop."""
    phrase = " ".join(f"word{i}" for i in range(100))
    benchmark(make_full_text, phrase)


# ── RPN conversion ────────────────────────────────────────────────────────────

def test_bench_to_rpn_simple(benchmark):
    """Shunting-yard on a 3-token query."""
    benchmark(_to_rpn, _SIMPLE_TOKENS)


def test_bench_to_rpn_complex(benchmark):
    """Shunting-yard on a 16-token nested query."""
    benchmark(_to_rpn, _COMPLEX_TOKENS)


# ── Boolean gates ─────────────────────────────────────────────────────────────

def test_bench_evaluate_and_full_overlap(benchmark):
    """AND on two 1 000-doc lists with 100 % overlap — all entries match."""
    left  = _large_posting_list(1000)
    right = _large_posting_list(1000)
    benchmark(_evaluate_and, left, right)


def test_bench_evaluate_and_no_overlap(benchmark):
    """AND on two 1 000-doc lists with 0 % overlap — produces empty result."""
    left  = _large_posting_list(1000, offset=0)
    right = _large_posting_list(1000, offset=1000)
    benchmark(_evaluate_and, left, right)


def test_bench_evaluate_or_no_overlap(benchmark):
    """OR on two 1 000-doc lists with 0 % overlap — 2 000-doc union."""
    left  = _large_posting_list(1000, offset=0)
    right = _large_posting_list(1000, offset=1000)
    benchmark(_evaluate_or, left, right)


# ── Database ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def bench_db():
    """Module-scoped in-memory DB shared across all DB benchmarks."""
    conn = sqlite3.connect(":memory:")
    initialise_db(conn)
    return conn


def test_bench_bulk_upsert_100_tokens(benchmark, bench_db):
    """Insert 100 tokens into a single page (with conflict accumulation)."""
    doc_id = get_or_create_doc_id(bench_db, "/bench/upsert.txt")
    token_tf_pairs = [(f"tok{i}", i + 1) for i in range(100)]
    benchmark(bulk_upsert_postings, bench_db, token_tf_pairs, doc_id, 1)


def test_bench_fetch_postings_50_docs(benchmark, bench_db):
    """Fetch postings for a token shared across 50 documents (JOIN query)."""
    for i in range(50):
        doc_id = get_or_create_doc_id(bench_db, f"/bench/doc_{i}.txt")
        bulk_upsert_postings(bench_db, [("common", 1)], doc_id, 1)
    bench_db.commit()
    benchmark(fetch_postings_for_token, bench_db, "common")
