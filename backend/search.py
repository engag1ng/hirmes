from backend.tokenizer import tokenize, tokenize_query
import dbm
import pickle
from backend.dictionary import dictionary

db_path = 'backend/index.db'

precedence = {
    "NOT": 3,
    "AND": 2,
}

right_associative = {"NOT"}

def is_operator(token):
    return token in {"AND", "NOT"}

def to_rpn(tokens):
    """Converts infix boolean expression to postfix (RPN) using Shunting Yard algorithm."""
    output = []
    stack = []
    for token in tokens:
        if token == '(':
            stack.append(token)
        elif token == ')':
            while stack and stack[-1] != '(':
                output.append(stack.pop())
            stack.pop()  # Remove '('
        elif is_operator(token):
            while (stack and stack[-1] != '(' and
                   ((token not in right_associative and precedence[token] <= precedence[stack[-1]]) or
                    (token in right_associative and precedence[token] < precedence[stack[-1]]))):
                output.append(stack.pop())
            stack.append(token)
        else:
            output.append(token)
    while stack:
        output.append(stack.pop())
    return output

def evaluate_rpn(rpn_tokens, db):
    """Evaluates the RPN expression using the document index in dbm."""
    stack = []
    for token in rpn_tokens:
        if is_operator(token):
            if token == "NOT":
                operand = stack.pop()
                all_docs = set()
                for key in db.keys():
                    all_docs.update(pickle.loads(db[key]))
                result = all_docs - operand
            else:
                right = stack.pop()
                left = stack.pop()
                if token == "AND":
                    result = left & right
            stack.append(result)
        else:
            try:
                doc_ids = pickle.loads(db[token.encode()])
            except KeyError:
                doc_ids = []
            stack.append(doc_ids)
    return stack[0] if stack else [] 

def search_index(query):
    tokenized_query = tokenize_query(query)
    spellchecked_query = spellcheck(tokenized_query)

    try: 
        with dbm.open(db_path, 'r') as db:
            rpn = to_rpn(spellchecked_query)
            result_docs = evaluate_rpn(rpn, db)
            print("Matching document IDs:", result_docs)
    except dbm.error:
        print("You have not indexed any documents yet, or the database could not be found.")

    return result_docs

LOGICAL_OPERATORS = {"AND", "NOT", "(", ")"}
def spellcheck(query):
    dic = dictionary()
    for i, word in enumerate(query):
        if word not in LOGICAL_OPERATORS:
            min_distance = float('inf')
            MAX_DISTANCE = max(1, len(word) // 3)
            ACCEPT_DISTANCE = max(1, len(word) // 4)
            closest_entry = None

            for entry in dic:
                if word in dic:
                    break
                dist = levenshtein_distance(word, entry)
                if dist <= ACCEPT_DISTANCE:
                    min_distance = 0
                    closest_entry = entry
                    break
                if dist < min_distance:
                    min_distance = dist
                    closest_entry = entry 

            if min_distance <= MAX_DISTANCE:
                query[i] = closest_entry
    return query

def levenshtein_distance(a: str, b: str) -> int:
    len_a = len(a)
    len_b = len(b)
    if len_b == 0:
        return len_a
    elif len_a == 0:
        return len_b
    elif a[0] == b[0]:
        return levenshtein_distance(a[1:], b[1:])
    else:
        return 1 + min(levenshtein_distance(a[1:], b), levenshtein_distance(a, b[1:]), levenshtein_distance(a[1:], b[1:]))