from tokenizer import tokenize, tokenize_query
import dbm
import pickle

db_path = '.backend/index.db'

query = input("What are you looking for? ")

precedence = {
    "NOT": 3,
    "AND": 2,
    "OR": 1
}

right_associative = {"NOT"}

def is_operator(token):
    return token in {"AND", "OR", "NOT"}

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
                elif token == "OR":
                    result = left | right
            stack.append(result)
        else:
            try:
                doc_ids = set(pickle.loads(db[token[0].encode()]))
            except KeyError:
                doc_ids = set()
            stack.append(doc_ids)
    return stack[0] if stack else set()

tokenized_query = tokenize_query(query)

try: 
    with dbm.open(db_path, 'r') as db:
        rpn = to_rpn(tokenized_query)
        result_docs = evaluate_rpn(rpn, db)
        print("Matching document IDs:", result_docs)
except dbm.error:
    print("You have not indexed any documents yet, or the database could not be found.")