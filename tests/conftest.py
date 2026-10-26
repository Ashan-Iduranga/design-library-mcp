"""Shared test setup: every test gets its own empty library in a temp folder."""

import pytest

from designlib.core.index import save_and_index
from designlib.core.schema import Entry


@pytest.fixture(autouse=True)
def temp_library(tmp_path, monkeypatch):
    library = tmp_path / "library"
    (library / "entries").mkdir(parents=True)
    (library / "styles").mkdir()
    (library / "assets" / "mine").mkdir(parents=True)
    monkeypatch.setenv("DESIGNLIB_LIBRARY", str(library))
    # Tests use keyword search unless a test turns semantic search on (test_semantic.py).
    monkeypatch.setenv("DESIGNLIB_SEMANTIC", "0")
    return library


def make_entry(**overrides) -> Entry:
    data = {
        "id": "sample-card-000001",
        "title": "Sample card",
        "source": "Test",
        "type": "component",
        "tags": ["card"],
    }
    data.update(overrides)
    return Entry(**data)


@pytest.fixture
def sample_entries():
    """A small library with a mix of types, tags and ratings."""
    entries = [
        make_entry(
            id="pricing-table-aaaaaa",
            title="Pricing table with toggle",
            source="HyperUI",
            license="MIT",
            tags=["pricing", "saas", "table"],
            framework="tailwind",
            code="<div class='p-4'>Pricing</div>",
            my_rating=5,
            favorite=True,
        ),
        make_entry(
            id="calm-dashboard-bbbbbb",
            title="Calm analytics dashboard",
            source="Godly",
            type="screen",
            tags=["dashboard", "dark"],
            style_notes={"palette": "slate and teal", "mood": "calm, focused"},
            my_rating=4,
        ),
        make_entry(
            id="glass-buttons-cccccc",
            title="Glass buttons",
            source="Uiverse",
            license="MIT",
            tags=["button", "glassmorphism"],
            framework="html",
            code="<button>Go</button>",
            my_rating=2,
        ),
    ]
    for entry in entries:
        save_and_index(entry)
    return entries
