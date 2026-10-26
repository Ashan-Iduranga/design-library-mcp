"""Semantic search tests.

Most tests replace the model with a tiny fake embedder (word buckets + a few
synonyms), so they run in milliseconds and still exercise sqlite-vec, syncing
and rank fusion for real. The last test uses the real model when it's installed.
"""

import hashlib
import math

import pytest

pytest.importorskip("sqlite_vec", reason="semantic extra not installed")

from conftest import make_entry  # noqa: E402
from designlib.core import semantic  # noqa: E402
from designlib.core.index import delete_and_unindex, save_and_index  # noqa: E402
from designlib.core.search import Filters, search  # noqa: E402

SYNONYMS = {"spinner": "loader", "waiting": "loading", "plan": "pricing"}


def fake_encode(texts):
    """Bag of words hashed into 384 buckets, with synonyms mapped to one word."""
    vectors = []
    for text in texts:
        vector = [0.0] * semantic.DIMENSIONS
        for word in text.lower().replace(",", " ").split():
            word = SYNONYMS.get(word, word)
            vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % semantic.DIMENSIONS] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        vectors.append([v / norm for v in vector])
    return vectors


@pytest.fixture
def fake_semantic(monkeypatch):
    calls = []

    def counting_encode(texts):
        calls.append(len(texts))
        return fake_encode(texts)

    monkeypatch.setenv("DESIGNLIB_SEMANTIC", "1")
    monkeypatch.setattr(semantic, "encode", counting_encode)
    monkeypatch.setattr(semantic, "MAX_DISTANCE", 0.95)
    return calls


@pytest.fixture
def library():
    for entry in [
        make_entry(id="loader-ring-aaaaaa", title="Ring loader", tags=["loader"], type="interaction"),
        make_entry(id="pricing-cards-bbbbbb", title="Pricing cards", tags=["pricing", "saas"]),
        make_entry(id="hero-split-cccccc", title="Split hero", tags=["hero"], type="layout"),
    ]:
        save_and_index(entry)


def ids(results):
    return [entry.id for entry in results]


def test_sync_embeds_only_what_changed(fake_semantic, library):
    assert semantic.sync() == 3
    assert semantic.sync() == 0  # nothing changed

    entry = search(Filters(query="hero", mode="keyword"))[0]
    entry.favorite = True  # same words -> no new embedding
    save_and_index(entry)
    assert semantic.sync() == 0

    entry.title = "Split hero with product sketch"  # new words -> re-embed
    save_and_index(entry)
    assert semantic.sync() == 1

    delete_and_unindex(entry.id)
    semantic.sync()
    assert "hero-split-cccccc" not in semantic.nearest("hero")


def test_meaning_finds_entries_without_shared_words(fake_semantic, library):
    assert search(Filters(query="spinner", mode="keyword")) == []
    assert ids(search(Filters(query="spinner")))[0] == "loader-ring-aaaaaa"
    assert ids(search(Filters(query="choose a plan")))[0] == "pricing-cards-bbbbbb"


def test_filters_still_apply_to_meaning_results(fake_semantic, library):
    assert search(Filters(query="spinner", type="layout")) == []
    assert ids(search(Filters(query="spinner", type="interaction"))) == ["loader-ring-aaaaaa"]


def test_entry_in_both_lists_ranks_first(fake_semantic, library):
    # "pricing" matches pricing-cards by keyword AND by meaning
    assert ids(search(Filters(query="pricing")))[0] == "pricing-cards-bbbbbb"


def test_gallery_does_not_wait_for_the_model(fake_semantic, library, monkeypatch):
    from fastapi.testclient import TestClient

    from designlib.web.app import create_app

    monkeypatch.setattr(semantic, "warm_up", lambda: None)
    client = TestClient(create_app())
    monkeypatch.setattr(semantic, "_model", None)  # model still loading
    page = client.get("/?q=spinner", headers={"HX-Request": "true"}).text
    assert "matched by meaning" not in page and "Ring loader" not in page

    monkeypatch.setattr(semantic, "_model", object())  # model ready
    page = client.get("/?q=spinner", headers={"HX-Request": "true"}).text
    assert "matched by meaning" in page and "Ring loader" in page


def test_failure_falls_back_to_keywords(fake_semantic, library, monkeypatch, capsys):
    def broken(*args, **kwargs):
        raise RuntimeError("model file corrupted")

    monkeypatch.setattr(semantic, "nearest", broken)
    assert ids(search(Filters(query="pricing"))) == ["pricing-cards-bbbbbb"]
    assert "using keywords only" in capsys.readouterr().err


def test_disabled_means_keyword_only(library, monkeypatch):
    monkeypatch.setenv("DESIGNLIB_SEMANTIC", "0")
    assert search(Filters(query="spinner")) == []


def _real_model_available() -> bool:
    if not semantic.installed():
        return False
    try:
        semantic._load_model()
    except Exception:
        return False
    return True


@pytest.mark.slow  # loads PyTorch (~10 s); skip with: pytest -m "not slow"
def test_real_model_understands_meaning(library, monkeypatch):
    if not _real_model_available():  # checked here, not in a decorator, so collection stays fast
        pytest.skip("all-MiniLM-L6-v2 not downloaded")
    monkeypatch.setenv("DESIGNLIB_SEMANTIC", "1")
    for query, expected in [("spinner while waiting", "loader-ring-aaaaaa"), ("monthly cost", "pricing-cards-bbbbbb")]:
        assert search(Filters(query=query, mode="keyword")) == []  # no shared words...
        assert ids(search(Filters(query=query)))[0] == expected  # ...but the meaning matches
