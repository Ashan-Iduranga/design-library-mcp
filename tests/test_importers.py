"""Importer tests build tiny fake repo zips in memory, so nothing is downloaded."""

import io
import zipfile

import pytest

from designlib.core.search import Filters, search
from designlib.core.storage import load_entry, save_entry
from designlib.importers import hyperui, uiverse
from designlib.importers.common import ImportStopped, round_robin, save_imported, verify_license

MIT = "MIT License\n\nCopyright (c) Someone\n\nPermission is hereby granted, free of charge, to any person..."


def make_zip(files: dict[str, str]) -> zipfile.ZipFile:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, text in files.items():
            archive.writestr(name, text)
    buffer.seek(0)
    return zipfile.ZipFile(buffer)


def test_license_check_accepts_mit_and_rejects_others():
    assert verify_license(make_zip({"repo-main/LICENSE": MIT}), "MIT") == "MIT License"
    with pytest.raises(ImportStopped, match="does not look like MIT"):
        verify_license(make_zip({"repo-main/LICENSE": "All rights reserved."}), "MIT")
    with pytest.raises(ImportStopped, match="no LICENSE"):
        verify_license(make_zip({"repo-main/README.md": "hi"}), "MIT")


HYPERUI_MDX = """---
title: Accordions
category: application
terms:
  - collapse
components:
  - title: Base
    description: Simple accordion
    dark: true
  - title: Compact
    description: Smaller text
---
body
"""

HYPERUI_EXAMPLE = """<!doctype html><html><head><link href="/component.css" rel="stylesheet"></head>
<body class="mx-auto max-w-3xl p-6 dark:bg-gray-900"><details class="group"><summary>Q</summary>A</details></body></html>"""


def hyperui_zip():
    return make_zip({
        "hyperui-main/LICENSE": MIT,
        "hyperui-main/src/content/collection/application/accordions.mdx": HYPERUI_MDX,
        "hyperui-main/public/examples/application/accordions/1.html": HYPERUI_EXAMPLE,
        "hyperui-main/public/examples/application/accordions/1-dark.html": HYPERUI_EXAMPLE,
        "hyperui-main/public/examples/application/accordions/2.html": HYPERUI_EXAMPLE,
    })


def test_hyperui_collect():
    groups = hyperui.collect(hyperui_zip())
    entries = groups["application/accordions"]
    assert [e.id for e in entries] == ["hyperui-application-accordions-1", "hyperui-application-accordions-2"]
    first = entries[0]
    assert first.title == "Accordions: Base"
    assert first.license == "MIT" and first.framework.value == "tailwind"
    assert {"application", "accordions", "collapse"} <= set(first.tags)
    assert first.code.startswith('<div class="mx-auto max-w-3xl p-6">')  # body classes kept, dark: dropped
    assert "component.css" not in first.code
    assert "github.com/markmead/hyperui/blob/main/public/examples/application/accordions/1.html" in first.notes


def test_hyperui_dark_variants_are_optional():
    groups = hyperui.collect(hyperui_zip(), include_dark=True)
    assert "hyperui-application-accordions-1-dark" in [e.id for e in groups["application/accordions"]]


UIVERSE_CSS = """<button class="cta">Go</button>
<style>
/* From Uiverse.io by 0x-Sarthak  - Tags: button, hover, rounded */
.cta { color: red; }
</style>"""

UIVERSE_TAILWIND = """<!-- From Uiverse.io by someone  - Tags: simple, button, tailwind -->
<button class="bg-blue-500 text-white">Go</button>"""


def test_uiverse_collect_detects_framework_and_credit():
    archive = make_zip({
        "galaxy-main/LICENSE": MIT,
        "galaxy-main/Buttons/0x-Sarthak_hungry-penguin-30.html": UIVERSE_CSS,
        "galaxy-main/Buttons/someone_calm-cat-1.html": UIVERSE_TAILWIND,
        "galaxy-main/Patterns/bob_dots-2.html": UIVERSE_CSS,
        "galaxy-main/README.md": "x",
    })
    groups = uiverse.collect(archive)
    css, tw = groups["Buttons"]
    assert css.title == "Button by 0x-Sarthak (hungry-penguin-30)"
    assert css.framework.value == "html" and tw.framework.value == "tailwind"
    assert css.url == "https://uiverse.io/0x-Sarthak/hungry-penguin-30"
    assert css.tags[:3] == ["button", "uiverse", "hover"]
    assert "tailwind" not in tw.tags
    assert groups["Patterns"][0].type.value == "style"
    assert list(uiverse.collect(archive, ["patterns"])) == ["Patterns"]


def test_round_robin_spreads_across_groups():
    picked = list(round_robin({"a": [1, 2, 3], "b": [10, 20]}, limit=3))
    assert picked == [1, 10, 2]
    assert len(list(round_robin({"a": [1, 2], "b": [3]}, limit=0))) == 3


def test_reimport_keeps_user_edits():
    entry = hyperui.collect(hyperui_zip())["application/accordions"][0]
    save_imported([entry])

    mine = load_entry(entry.id)
    mine.my_rating, mine.favorite, mine.when_to_use = 5, True, "FAQ pages"
    save_entry(mine)

    fresh = hyperui.collect(hyperui_zip())["application/accordions"][0]
    assert save_imported([fresh]) == (0, 1)
    kept = load_entry(entry.id)
    assert (kept.my_rating, kept.favorite, kept.when_to_use) == (5, True, "FAQ pages")
    assert search(Filters(query="accordion"))[0].id == entry.id


def write_zip(path, files: dict[str, str]):
    with zipfile.ZipFile(path, "w") as archive:
        for name, text in files.items():
            archive.writestr(name, text)
    return path


def test_hyperui_run_end_to_end(tmp_path, monkeypatch):
    """run() = (cached) download -> license check -> collect -> save, with no network."""
    archive = write_zip(tmp_path / "repo.zip", {n: hyperui_zip().read(n).decode() for n in hyperui_zip().namelist()})
    monkeypatch.setattr(hyperui, "download_repo", lambda *a, **k: archive)
    assert hyperui.run(limit=1) == (1, 0)
    assert load_entry("hyperui-application-accordions-1").source == "HyperUI"


def test_cli_import_stops_on_wrong_license(tmp_path, monkeypatch, capsys):
    from designlib.cli import main

    archive = write_zip(tmp_path / "repo.zip", {
        "galaxy-main/LICENSE": "Copyright Someone. All rights reserved.",
        "galaxy-main/Buttons/a_b-1.html": UIVERSE_CSS,
    })
    monkeypatch.setattr(uiverse, "download_repo", lambda *a, **k: archive)
    with pytest.raises(SystemExit, match="Import stopped: LICENSE does not look like MIT"):
        main(["import", "uiverse"])
    assert search(Filters()) == []  # nothing was saved


def test_cli_import_reports_counts(tmp_path, monkeypatch, capsys):
    from designlib.cli import main

    archive = write_zip(tmp_path / "repo.zip", {
        "galaxy-main/LICENSE": MIT,
        "galaxy-main/Buttons/a_b-1.html": UIVERSE_CSS,
        "galaxy-main/Cards/c_d-2.html": UIVERSE_TAILWIND,
    })
    monkeypatch.setattr(uiverse, "download_repo", lambda *a, **k: archive)
    main(["import", "uiverse", "--category", "cards"])
    assert "1 new, 0 updated" in capsys.readouterr().out
