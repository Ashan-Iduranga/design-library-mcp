import pytest
from fastapi.testclient import TestClient

from designlib.core import fetch
from designlib.core.fetch import PageMeta
from designlib.core.search import get_entry
from designlib.web.app import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_empty_library_shows_empty_state(client):
    page = client.get("/")
    assert page.status_code == 200
    assert "Your library is empty" in page.text


def test_home_lists_cards_and_facets(client, sample_entries):
    page = client.get("/").text
    assert "Pricing table with toggle" in page
    assert 'name="tag" value="pricing"' in page  # tag chip
    assert "3 references" in page


def test_htmx_request_returns_only_results(client, sample_entries):
    page = client.get("/?q=glass", headers={"HX-Request": "true"}).text
    assert "<html" not in page
    assert "Glass buttons" in page and "Pricing table" not in page


def test_filters_in_query_string(client, sample_entries):
    page = client.get("/?type=screen&sort=title").text
    assert "Calm analytics dashboard" in page and "Glass buttons" not in page
    assert "Nothing matches" in client.get("/?tag=pricing&tag=dark").text


def test_code_entries_render_sandboxed_iframe(client, sample_entries):
    page = client.get("/d/pricing-table-aaaaaa").text
    assert 'sandbox="allow-scripts"' in page
    assert "allow-same-origin" not in page
    assert "tailwind-browser.js" in page  # tailwind entries load the vendored build


def test_detail_404(client):
    assert client.get("/d/missing-entry").status_code == 404


def test_create_edit_delete_flow(client):
    form = {
        "title": "Bento feature grid",
        "url": "https://example.com/bento",
        "type": "layout",
        "framework": "none",
        "license": "link-only",
        "tags": "bento, grid",
        "my_rating": "4",
        "notes": "Uneven tiles",
    }
    created = client.post("/new", data=form, follow_redirects=False)
    assert created.status_code == 303
    entry_id = created.headers["location"].removeprefix("/d/")
    assert get_entry(entry_id).tags == ["bento", "grid"]

    form["title"] = "Bento grid v2"
    form["favorite"] = "on"
    client.post(f"/d/{entry_id}/edit", data=form)
    edited = get_entry(entry_id)
    assert edited.title == "Bento grid v2" and edited.favorite

    client.post(f"/d/{entry_id}/delete")
    assert get_entry(entry_id) is None


def test_form_rejects_code_without_open_license(client):
    response = client.post(
        "/new",
        data={"title": "Copied thing", "type": "component", "license": "link-only", "code": "<div></div>"},
    )
    assert response.status_code == 422
    assert "open licenses" in response.text


def test_screenshot_upload(client, temp_library):
    response = client.post(
        "/new",
        data={"title": "My shot", "type": "screen", "license": "Own"},
        files={"screenshot": ("shot.png", b"\x89PNG fake", "image/png")},
        follow_redirects=False,
    )
    entry = get_entry(response.headers["location"].removeprefix("/d/"))
    assert entry.local_image == f"assets/mine/{entry.id}.png"
    assert (temp_library / entry.local_image).exists()
    assert client.get("/" + entry.local_image).status_code == 200


def test_upload_rejects_non_images(client):
    response = client.post(
        "/new",
        data={"title": "Bad", "type": "screen"},
        files={"screenshot": ("evil.html", b"<script>", "text/html")},
    )
    assert response.status_code == 422


def test_favorite_toggle_returns_button(client, sample_entries):
    html = client.post("/d/calm-dashboard-bbbbbb/favorite").text
    assert 'aria-pressed="true"' in html
    assert get_entry("calm-dashboard-bbbbbb").favorite


def test_meta_api(client, monkeypatch):
    monkeypatch.setattr(fetch, "fetch_metadata", lambda url: PageMeta(url=url, title="Hi", source="X"))
    assert client.get("/api/meta", params={"url": "https://x.dev"}).json()["title"] == "Hi"


def test_tags_and_sources_pages(client, sample_entries, temp_library):
    (temp_library / "sources.md").write_text("# Sources\n\n| A | B |\n|---|---|\n| HyperUI | MIT |\n", encoding="utf-8")
    assert "#pricing" in client.get("/tags").text
    sources = client.get("/sources").text
    assert "<table>" in sources and "HyperUI" in sources


def test_grid_thumbnails_hide_scrollbars_but_detail_does_not(client, sample_entries):
    assert "overflow: hidden" in client.get("/").text
    assert "overflow: hidden" not in client.get("/d/pricing-table-aaaaaa").text


def test_history_restore_gets_full_page(client, sample_entries):
    """Back button after an HTMX update: htmx asks for the whole page, not the partial."""
    page = client.get("/?q=glass", headers={"HX-Request": "true", "HX-History-Restore-Request": "true"}).text
    assert "<html" in page


def test_link_only_entry_shows_hotlinked_image(client):
    from conftest import make_entry
    from designlib.core.index import save_and_index

    save_and_index(make_entry(id="shot-zzzzzz", type="screen", preview_image_url="https://example.com/og.png"))
    page = client.get("/").text
    assert 'src="https://example.com/og.png"' in page
    assert 'referrerpolicy="no-referrer"' in page
    assert "<iframe" not in page


def test_upload_size_limit(client, monkeypatch):
    from designlib.web import app as web_app

    monkeypatch.setattr(web_app, "MAX_UPLOAD_BYTES", 10)
    response = client.post(
        "/new",
        data={"title": "Huge", "type": "screen"},
        files={"screenshot": ("big.png", b"x" * 50, "image/png")},
    )
    assert response.status_code == 422 and "larger than 5 MB" in response.text


def test_remove_screenshot_on_edit(client):
    created = client.post(
        "/new",
        data={"title": "Shot", "type": "screen"},
        files={"screenshot": ("a.png", b"png", "image/png")},
        follow_redirects=False,
    )
    entry_id = created.headers["location"].removeprefix("/d/")
    client.post(f"/d/{entry_id}/edit", data={"title": "Shot", "type": "screen", "remove_image": "on"})
    assert get_entry(entry_id).local_image is None


def test_edit_keeps_added_at(client, sample_entries):
    before = get_entry("glass-buttons-cccccc").added_at
    client.post("/d/glass-buttons-cccccc/edit", data={"title": "Glass buttons", "type": "component",
                                                      "license": "MIT", "framework": "html", "code": "<b>x</b>"})
    assert get_entry("glass-buttons-cccccc").added_at == before


def test_meta_api_reports_fetch_errors(client, monkeypatch):
    def refuse(url):
        raise fetch.FetchError("robots.txt does not allow fetching this page")

    monkeypatch.setattr(fetch, "fetch_metadata", refuse)
    response = client.get("/api/meta", params={"url": "https://x.dev"})
    assert response.status_code == 422 and "robots.txt" in response.json()["error"]


def test_edit_and_delete_unknown_entry_404(client):
    assert client.get("/d/nope/edit").status_code == 404
    assert client.post("/d/nope/delete").status_code == 404
