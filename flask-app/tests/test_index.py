from backend.indexer import fn_index_path

path = 'F:\\auto-id-test\\biblio'

def test_indexing_speed(benchmark):
    result = benchmark(fn_index_path(path, True, True))
    assert benchmark.stats.stats['mean'] < 120