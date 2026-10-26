from designlib.core.search import Filters, list_sources, list_tags, search, to_fts_query


def ids(results):
    return [entry.id for entry in results]


def test_empty_query_returns_everything(sample_entries):
    assert len(search(Filters())) == 3


def test_keyword_and_prefix_match(sample_entries):
    assert ids(search(Filters(query="pricing"))) == ["pricing-table-aaaaaa"]
    assert ids(search(Filters(query="dashb"))) == ["calm-dashboard-bbbbbb"]


def test_stemming_matches_plurals(sample_entries):
    assert "glass-buttons-cccccc" in ids(search(Filters(query="button")))


def test_style_notes_are_searchable(sample_entries):
    assert ids(search(Filters(query="teal calm"))) == ["calm-dashboard-bbbbbb"]


def test_fts_syntax_does_not_crash(sample_entries):
    assert to_fts_query('"OR - :*') == '"or"*'
    search(Filters(query='pricing" OR (title:'))


def test_filters(sample_entries):
    assert ids(search(Filters(type="screen"))) == ["calm-dashboard-bbbbbb"]
    assert ids(search(Filters(framework="html"))) == ["glass-buttons-cccccc"]
    assert ids(search(Filters(source="HyperUI"))) == ["pricing-table-aaaaaa"]
    assert ids(search(Filters(favorites_only=True))) == ["pricing-table-aaaaaa"]
    assert ids(search(Filters(tags=["pricing", "saas"]))) == ["pricing-table-aaaaaa"]
    assert ids(search(Filters(tags=["pricing", "dark"]))) == []


def test_sorts(sample_entries):
    assert ids(search(Filters(sort="rating")))[0] == "pricing-table-aaaaaa"
    assert ids(search(Filters(sort="title")))[0] == "calm-dashboard-bbbbbb"


def test_tag_and_source_counts(sample_entries):
    assert ("pricing", 1) in list_tags()
    assert {name for name, _ in list_sources()} == {"HyperUI", "Godly", "Uiverse"}
