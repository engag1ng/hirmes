import pytest
import requests
from backend.search import spellcheck
from backend.tokenizer import tokenize_query

response = requests.get("https://www.mit.edu/~ecprice/wordlist.10000")

if response.status_code == 200:
    word_list = response.text.splitlines()
    print(f"Loaded {len(word_list)} words.")
else:
    print(f"Failed to fetch word list: {response.status_code}")

test_cases = [
    ("bananna", "banana"),
    ("acommodate", "accommodate"),
    ("definately", "definitely"),
    ("APPLE", "apple"),
    ("BanAna", "banana"),
    ("speling", "spelling"),
    ("quikly", "quickly"),
    ("defanitly", "definitely"),
    ("apple", "apple"),
    ("banana", "banana"),
    ("friend", "friend"),
    ("quickly", "quickly"),
    ("really", "really"),
    ("accommodate", "accommodate")
]

@pytest.mark.parametrize("query,expected", test_cases)
def test_spellcheck_correctness(query, expected):
    tokenized_query = tokenize_query(query)
    tokenized_expected = tokenize_query(expected)
    result = spellcheck(tokenized_query, word_list)
    assert result == tokenized_expected, f"{query} → {result[0]} (expected {expected})"