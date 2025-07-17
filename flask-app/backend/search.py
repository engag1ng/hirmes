from backend.tokenizer import tokenize, tokenize_query
from collections import defaultdict
from backend.read import *
import re
import sqlite3
from importlib.resources import files
from symspellpy import SymSpell, Verbosity
import os

app_folder = os.path.join(os.getenv("APPDATA"), "Hirmes")
os.makedirs(app_folder, exist_ok=True)

db_path = os.path.join(app_folder, "index.db")

def is_operator(token):
    return token in {"AND", "OR", "NOT"}

precedence = {
    "NOT": 3,
    "AND": 2,
    "OR": 1
}
right_associative = {"NOT"}

def to_rpn(tokens):
    """Converts infix Boolean expression to RPN (postfix) using the Shunting Yard algorithm."""
    output = []
    stack = []

    for token in tokens:
        if token == "(":
            stack.append(token)
        elif token == ")":
            while stack and stack[-1] != "(":
                output.append(stack.pop())
            if not stack or stack[-1] != "(":
                raise ValueError("Mismatched parentheses")
            stack.pop()
        elif is_operator(token):
            while (
                stack and stack[-1] != "(" and
                (
                    (token not in right_associative and precedence[token] <= precedence[stack[-1]]) or
                    (token in right_associative and precedence[token] < precedence[stack[-1]])
                )
            ):
                output.append(stack.pop())
            stack.append(token)
        else:
            output.append(token)

    while stack:
        if stack[-1] == "(":
            raise ValueError("Mismatched parentheses")
        output.append(stack.pop())

    return output

def extract_doc_keys(entries):
    return set((path, page) for path, page, _ in entries)

def evaluate_rpn_ranked(rpn_tokens):
    """
    Evaluates an RPN boolean expression with AND, OR, NOT and returns ranked results.
    Ranking is based on number of terms matched, then total term frequency.
    """
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        stack = []
        for token in rpn_tokens:
            if is_operator(token):
                if token == "NOT":
                    operand = stack.pop()
                    operand_keys = set(operand.keys())

                    all_docs = defaultdict(lambda: {"match_count": 0, "total_tf": 0})
                    cur.execute("SELECT DISTINCT path, page FROM postings")
                    for path, page in cur.fetchall():
                        all_docs[(path, page)]

                    result = {k: v for k, v in all_docs.items() if k not in operand_keys}
                    stack.append(result)

                else:
                    try:
                        right = stack.pop()
                        left = stack.pop()
                    except IndexError:
                        return None

                    result = defaultdict(lambda: {"match_count": 0, "total_tf": 0, "terms": set()})

                    if token == "AND":
                        common_keys = left.keys() & right.keys()
                        for key in common_keys:
                            result[key]["match_count"] = left[key]["match_count"] + right[key]["match_count"]
                            result[key]["total_tf"] = left[key]["total_tf"] + right[key]["total_tf"]
                            result[key]["terms"] = left[key]["terms"] | right[key]["terms"]
                    elif token == "OR":
                        all_keys = left.keys() | right.keys()
                        for key in all_keys:
                            result[key]["match_count"] = left[key]["match_count"] + right[key]["match_count"]
                            result[key]["total_tf"] = left[key]["total_tf"] + right[key]["total_tf"]
                            result[key]["terms"] = left[key]["terms"] | right[key]["terms"]
                    stack.append(result)

            else:
                doc_map = defaultdict(lambda: {"match_count": 0, "total_tf": 0, "terms": set()})

                cur.execute('''
                    SELECT path, page, tf FROM postings
                    WHERE token = ?
                ''', (token,))
                rows = cur.fetchall()
                for path, page, tf in rows:
                    doc_map[(path, page)]["match_count"] += 1
                    doc_map[(path, page)]["total_tf"] += tf
                    doc_map[(path, page)]["terms"].add(token)

                stack.append(doc_map)

        conn.close()

        if len(stack) != 1:
            return None

        final_map = stack.pop()

        results = [
            [path, page, data["match_count"], data["total_tf"], data["terms"]]
            for (path, page), data in final_map.items()
        ]
        results.sort(key=lambda x: (-x[2], -x[3]))

        return results

    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return []

def search_index(query):
    dictionary_path = str(files("symspellpy") / "frequency_dictionary_en_82_765.txt")
    bigram_path = str(files("symspellpy") / "frequency_bigramdictionary_en_243_342.txt")
    spellchecked_query = spellcheck(query, dictionary_path, bigram_path)
    print("spellchecked")
    tokenized_query = tokenize_query(spellchecked_query)
    print("tokenized")
    rpn = to_rpn(tokenized_query)
    print("rpn'd")
    result_docs = evaluate_rpn_ranked(rpn)
    print("eval")
    if result_docs:
        for i, result in enumerate(result_docs):
            if i < 5:
                result.append(search_snippet(result))
            else:
                result.append([])
        print("Snippets searched")
        return result_docs
    else:
        return "Error" 

LOGICAL_OPERATORS = {"AND", "NOT", "OR", "(", ")"}
def spellcheck(query, dictionary_path, bigram_path):
    sym_spell = SymSpell()
    sym_spell.load_dictionary(dictionary_path, term_index=0, count_index=1)
    sym_spell.load_dictionary(bigram_path, term_index=0, count_index=2)
    suggestions = sym_spell.lookup_compound(query, max_edit_distance=2)

    return suggestions[0]

def search_snippet(result):
    tokens = result[4]
    page_num = result[1]-1
    NUM_TOKENS = len(tokens)
    NUM_SNIPPETS = 5
    CONTEXT_LENGTH = 5
    snippets = []
    for token in tokens:
        try:
            file_function = match_extractor(result[0])
            raw_content = file_function(result[0])
            content = raw_content[page_num] # Higher order filetype function -> read content -> filter page
            matches = context_windows(content, token, CONTEXT_LENGTH)
            if NUM_TOKENS <= NUM_SNIPPETS:
                snippets += matches[:NUM_SNIPPETS//NUM_TOKENS]
            else:
                snippets += matches[0]
        except FileNotFoundError:
            snippets.append("File Not Found")
            break
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