import pytest
from backend.search import spellcheck, search_index
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
    ("Mi namme is herre.","my name is here"),
    ("He is boing.", "he is being")
]

@pytest.mark.parametrize("query,expected", test_cases)
def test_spellcheck_correctness(query, expected):
    DICTIONARY_PATH = str(files("symspellpy") / "frequency_dictionary_en_82_765.txt")
    bigram_path = str(files("symspellpy") / "frequency_bigramdictionary_en_243_342.txt")
    result = spellcheck(query).term
    assert result == expected, f"{query} → {result} (expected {expected})"

query_tests = [
    "Chemie",
    "Synthetische AND Kunststoffe",
    "Tenside OR Polymerbausteine",
    "Chemie NOT Veresterung",
    "( Wasserstoff OR Veresterung ) NOT Chemie"
]

def test_search_speed():
    for query in query_tests:
        results, spellchecked_query = search_index(query)
        assert results != None and spellchecked_query
