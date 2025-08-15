import re
from backend.system import get_resource_path
from collections import Counter

LOGICAL_OPERATORS = {"AND", "NOT", "OR", "(", ")"}
def is_operator(token):
    return token in LOGICAL_OPERATORS

def return_stop_list():
    with open(stoplist_path, 'r', encoding="utf-8") as file:
        return set(file.read().split("\n"))

stoplist_path = get_resource_path("backend/stoplist.txt")
stoplist = return_stop_list()

def tokenize(content):
    content = re.sub(r'[%^&*~\[\]]', '', content)

    url_pattern = re.compile(r'\b(?:https?://)?(?:www\.)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?')
    urls = url_pattern.findall(content)
    content = url_pattern.sub('', content)

    clean_urls = []
    for url in urls:
        url = url.split('(')[0] if '(' in url and url.count('http') > 1 else url
        url = url.rstrip(').,;')
        if re.search(r'\.\w{2,5}(/|$)', url):
            clean_urls.append(url)
    clean_urls = list(set(clean_urls))

    content = re.sub(r'[()/:]', '', content)

    date_pattern = re.compile(r'\b(0?[1-9]|[12][0-9]|3[01])\.(0?[1-9]|1[0-2])\.(\d{4})\b')
    date_matches = date_pattern.findall(content)
    dates = ['.'.join(date) for date in date_matches]
    content = date_pattern.sub('', content)

    lines = [line.lstrip('#').strip() for line in content.splitlines() if line.strip()]
    tokens = []

    filter_set = set('“-. _,.' + ''.join(map(str, range(10))) + ''.join(f'{i:02}' for i in range(10)))
    filter_re = re.compile(r'[“\-_\.,0-9]{2,}')
    split_re = re.compile(r"[’']+")

    for line in lines:
        for word in line.split():
            word = word.strip('",.“”>`!?;=')
            if len(word) == 1 and word in filter_set:
                continue
            word = filter_re.sub('', word)
            if word:
                tokens.extend(split_re.split(word.lower()))

    filtered_tokens = [t for t in tokens if t and t not in stoplist]
    all_tokens = filtered_tokens + dates + clean_urls

    return all_tokens

def tokenize_query(query):
    pattern = r'\bAND\b|\bNOT\b|\bOR\b|\(|\)|\w+'
    tokens = re.findall(pattern, query)

    processed_tokens = []
    for token in tokens:
        if is_operator(token):
            processed_tokens.append(token)
        else:
            tokenized = tokenize(token.lower())
            if tokenized:
                term_tokens = tokenized[0]
                processed_tokens.append(term_tokens)

    return processed_tokens