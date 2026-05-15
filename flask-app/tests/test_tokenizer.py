"""
Tests for backend.tokenizer.

Covers: stop word removal, URL/date extraction, character filtering,
apostrophe splitting, markdown stripping, and query tokenization.

Run: pytest tests/test_tokenizer.py -v
"""

import re
import pytest
from backend.tokenizer import tokenize, tokenize_query, STOPLIST


# ── tokenize() ────────────────────────────────────────────────────────────────

class TestTokenize:

    def test_empty_string_returns_empty(self):
        assert tokenize("") == []

    def test_plain_word_survives(self):
        assert "python" in tokenize("python")

    def test_output_is_lowercase(self):
        tokens = tokenize("Hello World PYTHON")
        assert "Hello" not in tokens
        assert "PYTHON" not in tokens
        # Only non-URL/date tokens; those can have mixed case
        word_tokens = [t for t in tokens if "." not in t]
        assert all(t == t.lower() for t in word_tokens)

    def test_stop_words_removed(self):
        # Pick 5 known stop words and confirm they don't survive
        stop_sample = sorted(STOPLIST)[:5]
        text = " ".join(stop_sample) + " elephant"
        tokens = tokenize(text)
        for sw in stop_sample:
            assert sw not in tokens, f"Stop word '{sw}' survived tokenization"

    def test_only_stop_words_returns_empty(self):
        stop_sample = sorted(STOPLIST)[:10]
        text = " ".join(stop_sample)
        assert tokenize(text) == []

    def test_url_extracted(self):
        tokens = tokenize("visit https://example.com/path for info")
        assert any("example.com" in t for t in tokens)

    def test_url_not_duplicated(self):
        tokens = tokenize("visit https://example.com for details")
        matches = [t for t in tokens if "example.com" in t]
        assert len(matches) == 1, f"URL appeared {len(matches)} times: {matches}"

    def test_bare_domain_extracted_as_url(self):
        tokens = tokenize("check github.com for the source code")
        assert any("github.com" in t for t in tokens)

    def test_date_dd_mm_yyyy_extracted(self):
        tokens = tokenize("the event is on 15.06.2024 at noon")
        assert "15.06.2024" in tokens

    def test_date_single_digit_day_and_month(self):
        tokens = tokenize("deadline 1.1.2025 is close")
        dates = [t for t in tokens if re.match(r'\d+\.\d+\.\d{4}', t)]
        assert len(dates) == 1

    def test_date_not_duplicated(self):
        tokens = tokenize("deadline 01.01.2025 is soon")
        dates = [t for t in tokens if re.match(r'\d+\.\d+\.\d{4}', t)]
        assert len(dates) == 1

    def test_multiple_dates_all_extracted(self):
        tokens = tokenize("from 01.03.2023 to 31.12.2023")
        dates = [t for t in tokens if re.match(r'\d+\.\d+\.\d{4}', t)]
        assert len(dates) == 2

    def test_special_chars_percent_caret_stripped(self):
        tokens = tokenize("hello%world^test")
        joined = " ".join(tokens)
        assert "%" not in joined
        assert "^" not in joined

    def test_parentheses_removed_from_content(self):
        tokens = tokenize("(python) and [java]")
        joined = " ".join(tokens)
        assert "(" not in joined
        assert ")" not in joined
        assert "[" not in joined

    def test_markdown_heading_hash_stripped(self):
        tokens = tokenize("## Introduction to Algorithms")
        assert "introduction" in tokens
        joined = " ".join(tokens)
        assert "#" not in joined

    def test_apostrophe_splits_word(self):
        # "it's" splits on the apostrophe; the apostrophe itself must not survive
        tokens = tokenize("it's a wonderful life")
        assert "wonderful" in tokens
        joined = " ".join(tokens)
        assert "'" not in joined
        assert "’" not in joined  # right single quotation mark

    def test_double_hyphen_removed_by_filter_re(self):
        # FILTER_RE removes sequences of 2+ chars from [-"_.,0-9]
        tokens = tokenize("abc--def")
        for tok in tokens:
            assert "--" not in tok

    def test_multiple_urls_all_extracted(self):
        tokens = tokenize("see google.com and github.com for resources")
        url_like = [t for t in tokens if re.match(r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', t)]
        assert len(url_like) >= 2

    def test_non_url_dots_not_extracted_as_url(self):
        # "e.g." has a 1-char TLD → should NOT be extracted as a URL
        tokens = tokenize("use e.g. for examples")
        # "e.g." fails the ≥2-char TLD check; it should not appear as a URL token
        url_like = [t for t in tokens if t == "e.g." or t == "e.g"]
        assert len(url_like) == 0


# ── tokenize_query() ──────────────────────────────────────────────────────────

class TestTokenizeQuery:

    def test_single_term(self):
        assert tokenize_query("python") == ["python"]

    def test_and_operator_preserved(self):
        result = tokenize_query("python AND java")
        assert result == ["python", "AND", "java"]

    def test_or_operator_preserved(self):
        result = tokenize_query("dogs OR cats")
        assert result == ["dogs", "OR", "cats"]

    def test_not_operator_preserved(self):
        result = tokenize_query("NOT spam")
        assert result == ["NOT", "spam"]

    def test_parentheses_preserved_and_positioned(self):
        result = tokenize_query("( python OR java ) AND web")
        assert result[0] == "("
        assert ")" in result
        assert result.index("(") < result.index(")")

    def test_stop_word_term_silently_dropped(self):
        # A query term that is a stop word gets discarded; AND/OR operators remain
        stop_word = sorted(STOPLIST)[0]
        result = tokenize_query(f"python AND {stop_word}")
        assert stop_word not in result
        # Operator still present even though one operand vanished
        assert "AND" in result

    def test_operator_casing_preserved(self):
        result = tokenize_query("python AND java")
        assert "AND" in result
        assert "and" not in result

    def test_query_terms_lowercased(self):
        result = tokenize_query("Python AND Java")
        assert "python" in result
        assert "java" in result
        assert "Python" not in result

    def test_complex_query_structure_order(self):
        result = tokenize_query("( python OR java ) AND NOT web")
        open_idx = result.index("(")
        close_idx = result.index(")")
        assert open_idx < close_idx
        assert "AND" in result
        assert "NOT" in result
