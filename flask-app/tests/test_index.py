from backend.indexer import fn_index_path
from security_clean import clean 


path = 'F:\\auto-id-test\\biblio'

def test_indexing_speed(benchmark):
    result = benchmark.pedantic(fn_index_path, args=(path, True, False), iterations=1, rounds=1, warmup_rounds=0)
    assert result > 0
