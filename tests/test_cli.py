from designlib.cli import main
from designlib.core import library
from designlib.core.fetch import PageMeta
from designlib.core.storage import load_entry


def test_add_list_search(monkeypatch, capsys):
    # Pretend the site answered, so the test stays offline.
    monkeypatch.setattr(
        library,
        "fetch_metadata",
        lambda url: PageMeta(
            url=url,
            title="Acme Landing",
            description="Calm SaaS hero",
            image_url="https://example.com/og.png",
            source="Land-book",
        ),
    )
    main(["add", "https://land-book.com/acme", "--type", "screen", "--tags", "hero, SaaS", "--rating", "5"])
    out = capsys.readouterr().out
    entry_id = out.split()[1]
    entry = load_entry(entry_id)
    assert entry.title == "Acme Landing"
    assert entry.tags == ["hero", "saas"]
    assert entry.license == "link-only" and entry.code is None
    assert entry.notes == "Calm SaaS hero"
    assert entry.preview_image_url == "https://example.com/og.png"

    main(["list"])
    assert "Acme Landing" in capsys.readouterr().out

    main(["search", "calm", "--tags", "hero"])
    assert entry_id in capsys.readouterr().out

    main(["search", "nothing-like-this"])
    assert "No entries found." in capsys.readouterr().out


def test_add_without_fetch(capsys):
    main(["add", "https://godly.website/x", "--type", "style", "--no-fetch", "--title", "Bold editorial"])
    assert "Bold editorial" in capsys.readouterr().out


def test_rebuild(sample_entries, capsys):
    main(["rebuild"])
    assert "Indexed 3 entries." in capsys.readouterr().out
