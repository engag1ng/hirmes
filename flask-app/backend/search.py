"""
Index database search and spellcheck utilities.

Typical usage:
    results, spellchecked = search_index(query)
"""

import re
import os
import sqlite3
from importlib.resources import files
from symspellpy import SymSpell
from backend.tokenizer import tokenize_query # pylint: disable=import-error
from backend.read import match_extractor # pylint: disable=import-error
from backend.database import fetch_postings_by_doc_id, fetch_paths_for_doc_ids, fetch_all_doc_ids, delete_documents # pylint: disable=import-error
from backend.settings import APP_FOLDER # pylint: disable=import-error

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

    to_delete = []
    kept = []
    for result in result_docs:
        if not os.path.isfile(result["path"]):
            to_delete.append(result["path"])
            continue
        result["snippet"] = _search_snippet(result) if len(kept) < 5 else []
        kept.append(result)
    result_docs = kept

    conn = sqlite3.connect(DB_PATH)
    delete_documents(conn, to_delete)
    conn.commit()
    conn.close()
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

def _evaluate_or(left: list, right: list) -> list:
    """Evaluate OR via sorted merge union on doc_id.

    Args:
        left: Sorted posting list.
        right: Sorted posting list.

    Returns:
        result: Sorted posting list containing union.
    """
    result = []
    i, j = 0, 0
    ll, rl = len(left), len(right)
    while i < ll and j < rl:
        l, r = left[i], right[j]
        lid, rid = l["doc_id"], r["doc_id"]
        if lid < rid:
            result.append(l)
            i += 1
        elif lid > rid:
            result.append(r)
            j += 1
        else:
            result.append({
                "doc_id": lid,
                "match_count": l["match_count"] + r["match_count"],
                "total_tf": l["total_tf"] + r["total_tf"],
                "terms": l["terms"] | r["terms"],
                "pages": l["pages"] | r["pages"],
            })
            i += 1
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result

def _evaluate_and(left: list, right: list) -> list:
    """Evaluate AND via sorted merge intersection on doc_id.

    Args:
        left: Sorted posting list.
        right: Sorted posting list.

    Returns:
        result: Sorted posting list containing intersection.
    """
    result = []
    i, j = 0, 0
    ll, rl = len(left), len(right)
    while i < ll and j < rl:
        l, r = left[i], right[j]
        lid, rid = l["doc_id"], r["doc_id"]
        if lid < rid:
            i += 1
        elif lid > rid:
            j += 1
        else:
            result.append({
                "doc_id": lid,
                "match_count": l["match_count"] + r["match_count"],
                "total_tf": l["total_tf"] + r["total_tf"],
                "terms": l["terms"] | r["terms"],
                "pages": l["pages"] | r["pages"],
            })
            i += 1
            j += 1
    return result

def _evaluate_not(conn, operand: list) -> list:
    """Evaluate NOT via sorted merge difference on doc_id.

    Args:
        conn: SQLite3 connection object.
        operand: Sorted posting list of docs to exclude.

    Returns:
        result: Sorted posting list of all docs not in operand.
    """
    all_doc_ids = fetch_all_doc_ids(conn)
    result = []
    i, j = 0, 0
    while i < len(all_doc_ids) and j < len(operand):
        did = all_doc_ids[i]
        if did < operand[j]["doc_id"]:
            result.append({"doc_id": did, "match_count": 0, "total_tf": 0, "terms": set(), "pages": set()})
            i += 1
        elif did > operand[j]["doc_id"]:
            j += 1
        else:
            i += 1
            j += 1
    while i < len(all_doc_ids):
        result.append({"doc_id": all_doc_ids[i], "match_count": 0, "total_tf": 0, "terms": set(), "pages": set()})
        i += 1
    return result

def _evaluate_rpn_ranked(rpn_tokens: list) -> list | None:
    """Evaluates RPN boolean expression and returns ranked results.

    Ranking is based on number of terms matched, then total term frequency.
    Evaluates at the document level (doc_id), looks up paths in a single
    batch query at the end.

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

                stack.append(_evaluate_not(conn, operand))

            else:
                try:
                    right = stack.pop()
                    left = stack.pop()
                except IndexError:
                    conn.close()
                    return None

                if token == "and":
                    stack.append(_evaluate_and(left, right))
                elif token == "or":
                    stack.append(_evaluate_or(left, right))

        else:
            raw_rows = fetch_postings_by_doc_id(conn, token)
            posting_list = []
            current_doc_id = None
            current_entry = None
            for doc_id, page, tf in raw_rows:
                if doc_id != current_doc_id:
                    if current_entry is not None:
                        posting_list.append(current_entry)
                    current_doc_id = doc_id
                    current_entry = {
                        "doc_id": doc_id,
                        "match_count": 1,
                        "total_tf": tf,
                        "terms": {token},
                        "pages": {page},
                    }
                else:
                    current_entry["match_count"] += 1
                    current_entry["total_tf"] += tf
                    current_entry["pages"].add(page)
            if current_entry is not None:
                posting_list.append(current_entry)
            stack.append(posting_list)

    if len(stack) != 1:
        conn.close()
        return None

    final_list = stack.pop()
    id_to_path = fetch_paths_for_doc_ids(conn, [e["doc_id"] for e in final_list])
    conn.close()

    final_list.sort(key=lambda e: (-e["match_count"], -e["total_tf"]))

    return [
        {
            "path": id_to_path[e["doc_id"]],
            "page_numbers": sorted(e["pages"]),
            "match_terms": list(e["terms"]),
        }
        for e in final_list
        if e["doc_id"] in id_to_path
    ]

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
    """
    Converts query into full text search.

    Adds 'AND' between every word to effectively create a full text search.

    Args:
        query: string with the query

    Returns:
        String
    """
    return " AND ".join(query.split())
