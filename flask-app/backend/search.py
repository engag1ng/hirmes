"""
Index database search and spellcheck utilities.

Typical usage:
    results, spellchecked = search_index(query)
"""

import re
import os
import sqlite3
from importlib.resources import files
from collections import defaultdict
from symspellpy import SymSpell
from backend.tokenizer import tokenize_query # pylint: disable=import-error
from backend.read import match_extractor # pylint: disable=import-error
from backend.database import fetch_postings_for_token, fetch_all_documents # pylint: disable=import-error
from backend.system import template_exists

APP_FOLDER = os.path.join(os.getenv("APPDATA"), "Hirmes")
os.makedirs(APP_FOLDER, exist_ok=True)

DB_PATH = os.path.join(APP_FOLDER, "index.db")
LOGICAL_OPERATORS = {"and", "not", "or", "(", ")"}

DICTIONARY_PATH = str(files("symspellpy") / "frequency_dictionary_en_82_765.txt")
BIGRAM_PATH = str(files("symspellpy") / "frequency_bigramdictionary_en_243_342.txt")

sym_spell = SymSpell()
sym_spell.load_dictionary(DICTIONARY_PATH, term_index=0, count_index=1)
sym_spell.load_dictionary(BIGRAM_PATH, term_index=0, count_index=2)

def search_index(query: str) -> tuple | None:
    """Returns ranked matching documents for query and a spellchecked query.

    Args:
        query: String combination of search words and logical operators.

    Returns:
        result_docs: List of search results
                List[{path: str, page_numbers: list, matched_terms: list, snippet: list}] 
        spellchecked_query: String recommendation for "Did You Mean"
    """
    spellchecked_query = spellcheck(query).term

    tokenized_query = tokenize_query(query)
    rpn = _to_rpn(tokenized_query)
    result_docs = _evaluate_rpn_ranked(rpn)
    if not result_docs:
        return [], spellchecked_query


    for result_number, result in enumerate(result_docs):
        if result_number < 5:
            result["snippet"] = _search_snippet(result)
        else:
            result["snippet"] = []

    return result_docs, spellchecked_query

def spellcheck(text: str) -> str:
    """Spellcheck text against dictionary and bigram dictionary.

    Args:
        text: String to spellcheck
    
    Returns:
        str: Spellchecked text
    """

    suggestions = sym_spell.lookup_compound(text, max_edit_distance=2)

    return suggestions[0]

def _is_operator(token: str) -> bool:
    """Returns whether token is a logical operator.

    Args:
        token: String to check

    Returns:
        bool: True if token is logical operator.
    """

    return token in LOGICAL_OPERATORS

def _to_rpn(tokens: list) -> list:
    """
    Convert list of tokens into Reverse Polish Notation (RPN).

    Supports:
    - Operators: NOT, AND, OR
    - Parentheses: ( and )
    - Operands: numbers, words, etc.

    Args:
        tokens: List of string tokens.

    Returns:
        output_queue: list of RPN tokens
    
    Raises:
        ValueError: If there are unmatched paranthesis.
    """

    precedence = {
        "not": 3,
        "and": 2,
        "or": 1
    }
    right_associative = {"not"}

    output_queue = []
    operator_stack = []

    for token in tokens:
        tok = token.lower()

        if tok in precedence:
            while (operator_stack and operator_stack[-1].lower() in precedence and
                ((tok not in right_associative and
                    precedence[tok] <= precedence[operator_stack[-1].lower()]) or
                    (tok in right_associative and
                    precedence[tok] < precedence[operator_stack[-1].lower()]))):
                output_queue.append(operator_stack.pop())
            operator_stack.append(tok)
        elif token == "(":
            operator_stack.append(token)
        elif token == ")":
            while operator_stack and operator_stack[-1] != "(":
                output_queue.append(operator_stack.pop())
            if not operator_stack:
                raise ValueError("Mismatched parentheses")
            operator_stack.pop()
        else:
            output_queue.append(token)

    while operator_stack:
        if operator_stack[-1] in ("(", ")"):
            raise ValueError("Mismatched parentheses")
        output_queue.append(operator_stack.pop())

    return output_queue

def _evaluate_or(left: dict, right: dict, result: dict) -> dict:
    """Evaluate OR (|) gate and edit result accordingly.

    Args:
        left: Dictionary of left token.
        right: Dictionary of right token.
        result: Dictionary to be edited.

    Returns:
        result: Edited result dictionary.
    """
    all_keys = left.keys() | right.keys()
    for key in all_keys:
        result[key]["match_count"] = (
            left[key]["match_count"]
            + right[key]["match_count"]
        )
        result[key]["total_tf"] = left[key]["total_tf"] + right[key]["total_tf"]
        result[key]["terms"] = left[key]["terms"] | right[key]["terms"]
        result[key]["pages"] = left[key]["pages"] | right[key]["pages"]

    return result

def _evaluate_and(left: dict, right: dict, result: dict) -> dict:
    """Evaluates AND (&) gate and edit result accordingly.

    Args:
        left: Dictionary of left token.
        right: Dictionary of right token.
        result: Dictionary to be edited.

    Returns:
        result: Edited result dictionary.
    """
    common_keys = left.keys() & right.keys()
    for key in common_keys:
        result[key]["match_count"] = (
            left[key]["match_count"]
            + right[key]["match_count"]
        )
        result[key]["total_tf"] = left[key]["total_tf"] + right[key]["total_tf"]
        result[key]["terms"] = left[key]["terms"] | right[key]["terms"]
        result[key]["pages"] = left[key]["pages"] | right[key]["pages"]

    return result

def _evaluate_not(conn, operand: dict) -> dict:
    """Evaluate NOT (-) gate and edit result accordingly.

    Args:
        conn: SQLite3 connection object.
        operand: Dictionary of token that should be excluded.

    Returns:
        result: Edited result dictionary.
    """

    all_docs = fetch_all_documents(conn)

    excluded_paths = set(operand.keys())

    included_docs = all_docs.difference(excluded_paths)

    result = {
        doc_path: {"match_count": 0, "total_tf": 0, "terms": set(), "pages": set(), "path": ""}
        for doc_path in included_docs
    }

    return result

def _evaluate_rpn_ranked(rpn_tokens: list) -> list | None:
    """Evaluates RPN boolean expression and returns ranked results.


    Ranking is based on number of terms matched, then total term frequency.
    Evaluates at the document level (doc_id as key), but stores pages inside each doc.

    Args:
        rpn_tokens: List of tokens in RPN format.

    Returns:
        results: List[{path: str, page_numbers: list, matched_terms: list}] 
    """

    conn = sqlite3.connect(DB_PATH)

    stack = []

    for token in rpn_tokens:
        if _is_operator(token):
            if token == "not":
                try:
                    operand = stack.pop()
                except IndexError:
                    conn.close()
                    return None

                result = _evaluate_not(conn, operand)

                stack.append(result)

            else:
                try:
                    right = stack.pop()
                    left = stack.pop()
                except IndexError:
                    conn.close()
                    return None

                result = defaultdict(
                    lambda: {"match_count": 0, "total_tf": 0, "terms": set(), "pages": set()}
                )

                if token == "and":
                    result = _evaluate_and(left, right, result)

                elif token == "or":
                    result = _evaluate_or(left, right, result)

                stack.append(result)

        else:
            doc_map = defaultdict(
                lambda: {"match_count": 0, "total_tf": 0, "terms": set(), "pages": set(), "tags": set()}
            )
            for doc_path, page, tf in fetch_postings_for_token(conn, token):
                doc_map[doc_path]["match_count"] += 1
                doc_map[doc_path]["total_tf"] += tf
                doc_map[doc_path]["terms"].add(token)
                doc_map[doc_path]["pages"].add(page)

            stack.append(doc_map)

    if len(stack) != 1:
        conn.close()
        return None

    final_map = stack.pop()

    results = [
        (
            str(doc_path),
            sorted(list(data["pages"])),
            data["match_count"],
            data["total_tf"],
            list(data["terms"])
        )
        for doc_path, data in final_map.items()
    ]

    results.sort(key=lambda x: (-x[2], -x[3]))

    truncated_results = [
        {
            "path": doc_path,
            "page_numbers": pages,
            "match_terms": terms
        }
        for doc_path, pages, _mc, _tf, terms in results
    ]

    conn.close()

    return truncated_results

def _search_snippet(result: dict) -> list:
    """Finds snippets in document for all matched terms.

    Args:
        result: Dictionary containing the document path, 
                page numbers and matched terms.
    
    Returns:
        snippets: List of string snippets for matched terms.
    """
    path = result["path"]
    page_nums = result["page_numbers"]
    tokens = result["match_terms"]
    num_tokens = len(tokens)
    num_snippets = 5
    context_length = 5
    snippets = []
    file_function = match_extractor(path)
    raw_content = file_function(path)
    if not raw_content:
        snippets.append("File Not Found")
        return snippets

    for num in page_nums:
        # Higher order filetype function -> read content -> filter page
        document_content = raw_content[num-1]

        for token in tokens:
            matches = _context_windows(document_content, token, context_length)
            if num_tokens <= num_snippets:
                snippets += matches[:num_snippets//num_tokens]
            else:
                snippets += matches[0]

    return snippets

def _context_windows(text: str, word: str, n: int = 5) -> list:
    """
    Finds all occurrences of `word` and returns up to `n` words before and after

    The search results include punctuation and special characters.

    Args:
        text: String to search
        word: String search term
        n: Number of words to return before and after.

    Returns:
        list: All matches for word in text in string format.
    """
    pattern = (
        rf'(?:\b\w+[^\s\w]*\s+){{0,{n}}}'
        rf'\b{re.escape(word)}[^\s\w]*'
        rf'(?:\s+\w+[^\s\w]*){{0,{n}}}'
    )

    return re.findall(pattern, text, flags=re.IGNORECASE)

def make_full_text(query: str) -> str:
    split_query = query.split()
    new_query = []
    
    for i, word in enumerate(split_query):
        new_query.append(word)
        if i+1 != len(split_query):
            new_query.append('AND')
    
    full_text_query = " ".join(new_query)
    return full_text_query