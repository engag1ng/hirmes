from backend.tokenizer import tokenize, tokenize_query
from collections import defaultdict
from backend.read import *
from backend.database import *
import re
from importlib.resources import files
from symspellpy import SymSpell, Verbosity
import os
import json
import sqlite3

app_folder = os.path.join(os.getenv("APPDATA"), "Hirmes")
os.makedirs(app_folder, exist_ok=True)

db_path = os.path.join(app_folder, "index.db")

LOGICAL_OPERATORS = {"and", "not", "or", "(", ")"}
def is_operator(token):
    return token in LOGICAL_OPERATORS

def to_rpn(tokens):
    """
    Convert a list of tokens (strings) into Reverse Polish Notation (RPN)
    using the Shunting Yard algorithm.

    Supports:
    - Operators: NOT, AND, OR
    - Parentheses: ( and )
    - Operands: numbers, words, etc.
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

def extract_doc_keys(entries):
    return set((path, page) for path, page, _ in entries)

def evaluate_rpn_ranked(rpn_tokens, db_path):
    """
    Evaluates an RPN boolean expression with AND, OR, NOT and returns ranked results.
    Ranking is based on number of terms matched, then total term frequency.
    Evaluates at the document level (doc_id as key), but stores pages inside each doc.
    """

    def fetch_all_docs(cur):
        cur.execute("SELECT doc_id, path FROM Document")
        return {doc_id: path for doc_id, path in cur.fetchall()}

    def is_operator(tok):
        return tok.upper() in {"NOT", "AND", "OR"}

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    stack = []

    for token in rpn_tokens:
        tok = token.upper()

        if is_operator(tok):
            if tok == "NOT":
                operand = stack.pop()
                operand_keys = set(operand.keys())

                all_docs = fetch_all_docs(cur)
                result = defaultdict(lambda: {"match_count": 0, "total_tf": 0, "terms": set(), "pages": set()})

                for doc_id in all_docs.keys():
                    if doc_id not in operand_keys:
                        result[doc_id]

                stack.append(result)

            else:
                try:
                    right = stack.pop()
                    left = stack.pop()
                except IndexError:
                    conn.close()
                    return None

                result = defaultdict(lambda: {"match_count": 0, "total_tf": 0, "terms": set(), "pages": set()})

                if tok == "AND":
                    common_keys = left.keys() & right.keys()
                    for key in common_keys:
                        result[key]["match_count"] = left[key]["match_count"] + right[key]["match_count"]
                        result[key]["total_tf"] = left[key]["total_tf"] + right[key]["total_tf"]
                        result[key]["terms"] = left[key]["terms"] | right[key]["terms"]
                        result[key]["pages"] = left[key]["pages"] | right[key]["pages"]

                elif tok == "OR":
                    all_keys = left.keys() | right.keys()
                    for key in all_keys:
                        result[key]["match_count"] = left[key]["match_count"] + right[key]["match_count"]
                        result[key]["total_tf"] = left[key]["total_tf"] + right[key]["total_tf"]
                        result[key]["terms"] = left[key]["terms"] | right[key]["terms"]
                        result[key]["pages"] = left[key]["pages"] | right[key]["pages"]

                stack.append(result)

        else:
            postings = fetch_postings_for_token(conn, token)

            doc_map = defaultdict(lambda: {"match_count": 0, "total_tf": 0, "terms": set(), "pages": set()})
            for doc_path, page, tf in postings:
                doc_map[doc_path]["match_count"] += 1
                doc_map[doc_path]["total_tf"] += tf
                doc_map[doc_path]["terms"].add(token)
                doc_map[doc_path]["pages"].add(page)



            stack.append(doc_map)

    if len(stack) != 1:
        conn.close()
        return None

    final_map = stack.pop()

    results = []
    results = [
        [str(doc_path), sorted(list(data["pages"])), data["match_count"], data["total_tf"], list(data["terms"])] for doc_path, data in final_map.items()
    ]

    results.sort(key=lambda x: (-x[2], -x[3]))

    conn.close()
    return results

def fn_search_index(query):
    dictionary_path = str(files("symspellpy") / "frequency_dictionary_en_82_765.txt")
    bigram_path = str(files("symspellpy") / "frequency_bigramdictionary_en_243_342.txt")
#    spellchecked_query = spellcheck(query, dictionary_path, bigram_path).term
#    print(f"spellchecked: {spellchecked_query}")
#    tokenized_query = tokenize_query(spellchecked_query)
    tokenized_query = tokenize_query(query)
    rpn = to_rpn(tokenized_query)
    result_docs = evaluate_rpn_ranked(rpn, db_path)
    if result_docs:
        for i, result in enumerate(result_docs):
            if i < 5:
                result.append(search_snippet(result))
            else:
                result.append([])
        return result_docs
    else:
        return "Error" 

def spellcheck(query, dictionary_path, bigram_path):
    sym_spell = SymSpell()
    sym_spell.load_dictionary(dictionary_path, term_index=0, count_index=1)
    sym_spell.load_dictionary(bigram_path, term_index=0, count_index=2)
    suggestions = sym_spell.lookup_compound(query, max_edit_distance=2)

    return suggestions[0]

def search_snippet(result):
    path = result[0]
    page_nums = result[1]
    tokens = result[4]
    NUM_TOKENS = len(tokens)
    NUM_SNIPPETS = 5
    CONTEXT_LENGTH = 5
    snippets = []

    file_function = match_extractor(path)
    raw_content = file_function(path)
    if raw_content == 555:
        snippets.append("File Not Found")
        return snippets
    
    for num in page_nums:
        content = raw_content[num-1] # Higher order filetype function -> read content -> filter page

        for token in tokens:
            matches = context_windows(content, token, CONTEXT_LENGTH)
            if NUM_TOKENS <= NUM_SNIPPETS:
                snippets += matches[:NUM_SNIPPETS//NUM_TOKENS]
            else:
                snippets += matches[0]
    return snippets

def context_windows(text: str, word: str, n: int = 5):
    """
    Finds all occurrences of `word` and returns up to `n` words before and after each,
    including punctuation.
    """
    pattern = (
        rf'(?:\b\w+[^\s\w]*\s+){{0,{n}}}'
        rf'\b{re.escape(word)}[^\s\w]*'  
        rf'(?:\s+\w+[^\s\w]*){{0,{n}}}'  
    )

    return re.findall(pattern, text, flags=re.IGNORECASE)