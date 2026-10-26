"""Mobile sources and duplicate protection: dedupe rules and merging, `add` refusing
duplicates, each new importer's parsing (fake inputs, no downloads), mobile platform
rules and Framework7 phone previews."""

import pytest

from conftest import make_entry
from designlib.core import categorize, dedupe, library
from designlib.core.fetch import PageMeta
from designlib.core.index import save_and_index
from designlib.core.library import AlreadyInLibrary
from designlib.core.storage import load_entry
from designlib.importers import framework7, galleries, guidelines, konsta, nativeapps, reactnative
from designlib.importers.common import save_imported
from designlib.web.preview import build_srcdoc

# ---------- duplicates ----------


def test_same_docs_link_with_different_code_is_not_a_duplicate():
    a = make_entry(id="a", url="https://lib.dev/docs/button", license="MIT", code="<button>A</button>")
    b = make_entry(id="b", url="https://lib.dev/docs/button/", license="MIT", code="<button>B</button>")
    assert dedupe.find_groups([a, b]) == []


def test_identical_code_or_same_post_and_image_is_a_duplicate():
    a = make_entry(id="a", url="https://lib.dev/x", license="MIT", code="<b>same</b>")
    b = make_entry(id="b", url="https://lib.dev/y", license="MIT", code="<b>  same </b>")
    post = dict(url="https://x.com/a/status/1?s=20", preview_image_url="https://cdn/img.jpg")
    c, d = make_entry(id="c", **post), make_entry(id="d", url="http://www.x.com/a/status/1", preview_image_url="https://cdn/img.jpg")
    e = make_entry(id="e", url="https://x.com/a/status/1", preview_image_url="https://cdn/other.jpg")  # 2nd image
    groups = sorted(sorted(x.id for x in g) for g in dedupe.find_groups([a, b, c, d, e]))
    assert groups == [["a", "b"], ["c", "d"]]


def test_merge_keeps_your_edits_and_combines_tags():
    mine = make_entry(id="mine", tags=["card"], my_rating=5, categories=["pricing"], categories_manual=True)
    other = make_entry(id="other", tags=["saas"], favorite=True)
    kept, removed = dedupe.merge([other, mine])
    assert kept.id == "mine" and [r.id for r in removed] == ["other"]
    assert kept.tags == ["card", "saas"] and kept.favorite and kept.categories == ["pricing"]


def test_importers_skip_what_the_library_already_has(capsys):
    save_and_index(make_entry(id="existing", url="https://lib.dev/x", license="MIT", code="<b>x</b>"))
    copy = make_entry(id="new-copy", url="https://lib.dev/other", license="MIT", code="<b>x</b>")
    fresh = make_entry(id="fresh", license="MIT", code="<i>new</i>")
    assert save_imported([copy, fresh]) == (1, 0)
    assert load_entry("new-copy") is None and "Skipped 1 duplicates" in capsys.readouterr().out


def test_add_refuses_a_page_already_in_the_library(monkeypatch):
    monkeypatch.setattr(library, "fetch_metadata", lambda url: PageMeta(url=url, title="Acme", image_url="https://i/a.png"))
    first = library.add_from_url("https://acme.dev/", type="screen")
    with pytest.raises(AlreadyInLibrary) as already:
        library.add_from_url("https://www.acme.dev", type="screen")
    assert already.value.entry.id == first.id


# ---------- importers ----------


def test_framework7_keeps_static_screens_only():
    page = '<div class="page"><div class="navbar"><div class="title">Cards</div></div></div>'
    entry = framework7.build_entry("cards", page)
    assert entry.title == "Cards (Framework7 mobile screen)" and entry.framework.value == "html"
    assert framework7.build_entry("messages", page.replace("Cards", "${title}")) is None  # needs the app
    wrapped = f"<template>{page}</template><script>export default () => {{}}</script>"
    assert framework7.build_entry("stepper", wrapped).code == page  # router wrapper removed
    assert framework7.build_entry("calendar", page) is None  # drawn by JavaScript


def test_konsta_and_react_native_entries():
    k = konsta.build_entry("ActionSheet", "export default function Page() {}")
    assert k.title.startswith("Action Sheet") and k.url == "https://konstaui.com/react/action-sheet"
    p = reactnative.paper_entry("BottomNavigationBar", "code")
    assert p.framework.value == "react-native" and "npm install react-native-paper" in p.prompt
    r = reactnative.reusables_entry("button", "code")
    assert r.prompt == "npx @react-native-reusables/cli@latest add button"


def test_native_app_helpers():
    assert nativeapps.pick_screenshot(["a/screenshots/x.png", "a/screenshots/demo.gif"]) == "a/screenshots/demo.gif"
    readme = "# Jetnews\n\n![shot](x.png)\n\nJetnews is a sample [news](https://x) app.\n\nMore."
    assert nativeapps.first_paragraph(readme) == "Jetnews is a sample news app."


def test_gallery_and_guideline_url_filters():
    assert galleries.penpot_wanted("https://penpot.app/penpothub/libraries-templates/android-ui-kit")
    assert not galleries.penpot_wanted("https://penpot.app/penpothub/libraries-templates/submit")
    assert guidelines.m3_wanted("https://m3.material.io/components/app-bars/overview")
    assert not guidelines.m3_wanted("https://m3.material.io/components/app-bars/specs")
    assert guidelines.m3_wanted("https://m3.material.io/foundations/accessibility")
    fields = galleries.penpot_build(galleries.Page(
        url="https://penpot.app/penpothub/libraries-templates/mobile-ui-starter-kit", html="",
        meta=PageMeta(url="", title="Mobile UI Starter kit | Penpot", description="A kit.")))
    assert fields["title"] == "Mobile UI Starter kit (Penpot kit)" and "mobile-app" in fields["tags"]
    assert "CC BY 4.0" in fields["notes"]


# ---------- platform + previews ----------


def test_mobile_sources_are_mobile_even_as_web_code():
    f7 = framework7.build_entry("list", '<div class="page">list</div>')
    assert categorize.categorize(f7)[0] == "mobile"
    assert categorize.categorize(reactnative.paper_entry("Button", "x"))[0] == "mobile"
    hig = make_entry(title="Apple HIG: Tab bars", tags=["tab-bars", "guidelines", "ios"], source="Apple HIG")
    platform, cats = categorize.categorize(hig)
    assert platform == "mobile" and "navigation" in cats and "guidelines" in cats


def test_framework7_preview_has_theme_and_phone_layout():
    entry = framework7.build_entry("list", '<div class="page">list</div>')
    ios, md = build_srcdoc(entry), build_srcdoc(entry, theme="md")
    assert '<html class="ios device-ios">' in ios and '<html class="md device-md">' in md
    assert "framework7-bundle.min.css" in ios and 'class="framework7-root"' in ios and 'body class="phone"' in ios
