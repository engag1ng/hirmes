"""Tokenization functions for text and queries.

Typical usage:
    tokens = tokenize(text)

    tokenized_query = tokenize_query(query)
"""

import re
from backend.system import get_resource_path # pylint: disable=import-error

LOGICAL_OPERATORS = {"AND", "NOT", "OR", "(", ")"}
STOPLIST_PATH = get_resource_path("backend/stoplist.txt")
URL_PATTERN = re.compile(r'\b(?:https?://)?(?:www\.)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?')
DATE_PATTERN = re.compile(r'\b(0?[1-9]|[12][0-9]|3[01])\.(0?[1-9]|1[0-2])\.(\d{4})\b')
FILTER_RE = re.compile(r'[“\-_\.,0-9]{2,}')
SPLIT_RE = re.compile(r"[’']+")

def tokenize(content: str) -> list:
    """
    Tokenizes string.

    Finds URL's, dates, and filters stop words and special characters.

    Args:
        content: String to be tokenized.
    
    Returns:
        list: All tokens.
    """
    content = re.sub(r'[%^&*~\[\]]', '', content)

    urls = URL_PATTERN.findall(content)
    content = URL_PATTERN.sub('', content)

    clean_urls = []
    for url in urls:
        url = url.split('(')[0] if '(' in url and url.count('http') > 1 else url
        url = url.rstrip(').,;')
        if re.search(r'\.\w{2,5}(/|$)', url):
            clean_urls.append(url)
    clean_urls = list(set(clean_urls))

    content = re.sub(r'[()/:]', '', content)

    dates = ['.'.join(date) for date in DATE_PATTERN.findall(content)]
    content = DATE_PATTERN.sub('', content)

    lines = [line.lstrip('#').strip() for line in content.splitlines() if line.strip()]
    tokens = []

    filter_set = set(
        '“-. _,.' + ''.join(map(str, range(10))) + ''.join(f'{i:02}' for i in range(10))
    )

    for line in lines:
        for word in line.split():
            word = word.strip('",.“”>`!?;=')
            if len(word) == 1 and word in filter_set:
                continue
            word = FILTER_RE.sub('', word)
            if word:
                tokens.extend(SPLIT_RE.split(word.lower()))

    filtered_tokens = [t for t in tokens if t and t not in _return_stop_list()]

    return filtered_tokens + dates + clean_urls

def tokenize_query(query: str) -> list:
    """
    Tokenizes query in string format.

    Args:
        query: String query to be tokenized.
    
    Returns:
        processed_query: Query in tokenized list form.
    """
    pattern = r'\bAND\b|\bNOT\b|\bOR\b|\(|\)|\w+'
    tokens = re.findall(pattern, query)

    processed_query = []
    for token in tokens:
        if _is_operator(token):
            processed_query.append(token)
        else:
            tokenized = tokenize(token.lower())
            if tokenized:
                term_tokens = tokenized[0]
                processed_query.append(term_tokens)

    return processed_query

def _is_operator(token: str) -> bool:
    """
    Returns whether token is a logical operator.

    Args:
        token: String to test.

    Returns:
        True: If token is logical operator.
        False: Else.
    """
    return token in LOGICAL_OPERATORS

def _return_stop_list() -> set:
    """
    Returns content of stop list as set of strings.
    """
    with open(STOPLIST_PATH, 'r', encoding="utf-8") as file:
        return set(file.read().split("\n"))
