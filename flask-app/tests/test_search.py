import pytest
from backend.search import spellcheck
from importlib.resources import files
from symspellpy import SymSpell

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
    ("accommodate", "accommodate"),
    ("Mi namme is herre.","my name is here")
]

@pytest.mark.parametrize("query,expected", test_cases)
def test_spellcheck_correctness(query, expected):
    dictionary_path = str(files("symspellpy") / "frequency_dictionary_en_82_765.txt")
    bigram_path = str(files("symspellpy") / "frequency_bigramdictionary_en_243_342.txt")
    result = spellcheck(query, dictionary_path, bigram_path).term
    assert result == expected, f"{query} → {result} (expected {expected})"