"""Categories and platforms: taxonomy sanity, the categorizer per source, manual choices
being kept, filters and counts, the sidebar, the edit form and the MCP tool."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from conftest import make_entry
from designlib import mcp_server
from designlib.core import categorize, recategorize
from designlib.core.index import save_and_index
from designlib.core.schema import Entry
from designlib.core.search import Filters, category_counts, platform_counts, search
from designlib.core.storage import load_entry
from designlib.core.taxonomy import BY_SLUG, CATEGORIES, GROUPS
from designlib.web.app import create_app


def cats(**fields) -> tuple[str, list[str]]:
    return categorize.categorize(make_entry(**fields))


# ---------- taxonomy ----------


def test_every_keyword_points_to_one_category():
    seen: dict[str, str] = {}
    for category in CATEGORIES:
        assert category.group in GROUPS
        for keyword in (category.slug, *category.keywords):
            word = categorize.normalise(keyword)
            assert seen.setdefault(word, category.slug) == category.slug, f"{word!r} is in two categories"


def test_unknown_category_rejected_and_old_json_still_loads():
    with pytest.raises(ValidationError, match="unknown categories"):
        make_entry(categories=["not-a-category"])
    old = Entry.model_validate_json('{"id": "old-1", "title": "Old", "type": "component"}')
    assert old.platform.value == "any" and old.categories == []


# ---------- the categorizer, per kind of source ----------


def test_code_libraries():
    assert cats(source="HyperUI", title="Footers: Large with newsletter form",
                tags=["marketing", "footers", "hyperui"], framework="tailwind") == ("web", ["footer"])
    platform, found = cats(source="shadcn/ui", title="Login 01 (shadcn/ui block)",
                           tags=["block", "login", "authentication", "shadcn", "react"], framework="react")
    assert platform == "web" and found[0] == "auth"
    # an "iOS style" toggle written in HTML is still web code
    assert cats(source="Uiverse", title="Toggle by x (ios-switch)", tags=["toggle", "uiverse", "ios"],
                framework="html") == ("web", ["toggle"])


def test_galleries():
    platform, found = cats(source="Collect UI", title="Onboarding, Mobile App by @x: new flow",
                           tags=["onboarding", "mobile-app", "collectui", "video"])
    assert platform == "mobile" and found[0] == "onboarding" and "media" not in found  # "video" is ignored
    assert cats(source="Collect UI", title="Mac App by @y: menu bar", tags=["mac-app", "collectui"])[0] == "desktop"
    assert cats(source="SaaS Landing Page", title="Acme landing page",
                tags=["landing-page", "saas", "mobile-app"])[0] == "web"  # a site about an app


def test_design_style_comes_after_what_it_is():
    platform, found = cats(source="DesignPrompts", title="Button in Botanical style",
                           tags=["button", "botanical", "designprompts", "prompt"])
    assert found == ["button", "design-style"]


def test_icons_and_colors_work_on_any_platform():
    assert cats(source="Lucide", title="Lucide icons: Arrows (223)", tags=["icons", "arrows"],
                framework="html", license="ISC", code="<svg/>") == ("any", ["icons"])
    assert cats(source="Radix Colors", title="Radix Colors: Blue scale", type="palette",
                tags=["blue", "color-scale"])[0] == "any"


def test_unclear_entries_go_to_other():
    assert cats(source="Collect UI", title="Design by @z: wow", tags=["collectui", "video"]) == ("any", ["other"])


# ---------- saving, manual choices, re-running ----------


def test_saving_fills_in_categories():
    save_and_index(make_entry(id="hero-a", title="Hero: Split", tags=["hero"], source="HyperUI", framework="tailwind"))
    entry = load_entry("hero-a")
    assert entry.categories == ["hero"] and entry.platform.value == "web"


def test_manual_categories_survive_recategorize():
    save_and_index(make_entry(id="mine-1", title="Hero", tags=["hero"], categories=["pricing"],
                              platform="mobile", categories_manual=True))
    recategorize.run(force=True, use_meaning=False)
    entry = load_entry("mine-1")
    assert entry.categories == ["pricing"] and entry.platform.value == "mobile"


def test_platform_by_meaning_needs_a_clear_winner(monkeypatch):
    vectors = {"mobile": [1, 0, 0], "web": [0, 1, 0], "desktop": [0, 0, 1]}
    protos = [vectors[name] for name in categorize.PROTOTYPES]

    def fake_encode(texts):
        rest = [[0.9, 0.1, 0.0] if "phone" in t else [0.5, 0.5, 0.0] for t in texts[len(protos):]]
        return protos + rest

    monkeypatch.setattr("designlib.core.semantic.encode", fake_encode)
    assert categorize.platform_by_meaning(["a phone app", "something vague"]) == ["mobile", None]


# ---------- filters, counts, gallery, MCP ----------


@pytest.fixture
def mixed():
    for entry in [
        make_entry(id="w-hero", title="Hero A", tags=["hero"], source="HyperUI", framework="tailwind"),
        make_entry(id="w-price", title="Pricing B", tags=["pricing"], source="HyperUI", framework="tailwind"),
        make_entry(id="m-onb", title="Onboarding C", tags=["onboarding", "mobile-app"], source="Collect UI"),
    ]:
        save_and_index(entry)


def test_filters_and_counts(mixed):
    assert [e.id for e in search(Filters(platform="mobile"))] == ["m-onb"]
    assert [e.id for e in search(Filters(categories=["hero", "pricing"], sort="title"))] == ["w-hero", "w-price"]
    assert category_counts(Filters(platform="web")) == {"hero": 1, "pricing": 1}
    assert platform_counts(Filters(categories=["onboarding"])) == {"mobile": 1}
    assert [e.id for e in search(Filters(query="onboarding"))] == ["m-onb"]  # category names are searchable


def test_gallery_sidebar_and_tabs(mixed):
    client = TestClient(create_app())
    page = client.get("/?platform=web").text
    assert 'value="hero" checked' not in page and "Hero" in page and 'id="sidebar"' in page
    live = client.get("/?platform=web&category=hero", headers={"HX-Request": "true"}).text
    assert "Hero A" in live and "Pricing B" not in live
    assert live.count('hx-swap-oob="true"') == 2  # sidebar + platform tabs refreshed


def test_edit_form_marks_categories_as_manual(mixed):
    client = TestClient(create_app())
    form = {"title": "Hero A", "type": "component", "license": "MIT", "framework": "tailwind",
            "platform": "web", "categories": ["hero"]}
    client.post("/d/w-hero/edit", data=form)
    assert load_entry("w-hero").categories_manual is False  # unchanged from the automatic choice
    client.post("/d/w-hero/edit", data={**form, "categories": ["cta"]})
    entry = load_entry("w-hero")
    assert entry.categories == ["cta"] and entry.categories_manual is True


def test_mcp_category_tools(mixed):
    groups = mcp_server.list_categories(platform="web")
    labels = {c["slug"]: c["count"] for g in groups for c in g["categories"]}
    assert labels == {"hero": 1, "pricing": 1}
    results = mcp_server.search_designs(platform="mobile", category="onboarding")
    assert [r["id"] for r in results] == ["m-onb"] and results[0]["categories"] == ["onboarding"]
    assert BY_SLUG["onboarding"].group == "App screens"
