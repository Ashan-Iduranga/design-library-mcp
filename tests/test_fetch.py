"""Fetch tests use httpx.MockTransport, so no real website is ever contacted."""

import httpx
import pytest

from designlib.core import fetch
from designlib.core.fetch import FetchError, fetch_metadata, parse_meta, source_name

PAGE = """<html><head>
<title>  Fallback   Title </title>
<meta property="og:title" content="Acme Landing">
<meta name="description" content="A calm SaaS landing page.">
<meta property="og:image" content="/og/cover.png">
</head><body>ignored</body></html>"""


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(fetch, "MIN_DELAY_SECONDS", 0)


def mock_client(robots: str = "", page: str = PAGE, content_type: str = "text/html") -> tuple[httpx.Client, list]:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=robots) if robots else httpx.Response(404)
        return httpx.Response(200, text=page, headers={"content-type": content_type})

    client = httpx.Client(transport=httpx.MockTransport(handler), headers={"User-Agent": fetch.USER_AGENT})
    return client, seen


def test_parse_meta_prefers_og_and_resolves_image():
    meta = parse_meta(PAGE, "https://land-book.com/sites/acme")
    assert meta.title == "Acme Landing"
    assert meta.description == "A calm SaaS landing page."
    assert meta.image_url == "https://land-book.com/og/cover.png"
    assert meta.source == "Land-book"


def test_title_falls_back_to_title_tag():
    meta = parse_meta("<title> Only  this </title>", "https://example.com")
    assert meta.title == "Only this"
    assert meta.image_url is None


def test_fetch_checks_robots_first_and_sends_user_agent():
    client, seen = mock_client()
    meta = fetch_metadata("https://example.com/page", client=client)
    assert meta.title == "Acme Landing"
    assert [r.url.path for r in seen] == ["/robots.txt", "/page"]
    assert all(r.headers["user-agent"] == fetch.USER_AGENT for r in seen)


def test_robots_disallow_stops_fetch():
    client, seen = mock_client(robots="User-agent: *\nDisallow: /")
    with pytest.raises(FetchError, match="robots.txt"):
        fetch_metadata("https://example.com/page", client=client)
    assert [r.url.path for r in seen] == ["/robots.txt"]  # the page itself was never requested


def test_non_html_rejected():
    client, _ = mock_client(content_type="image/png")
    with pytest.raises(FetchError, match="not an HTML page"):
        fetch_metadata("https://example.com/pic.png", client=client)


def test_only_http_urls():
    with pytest.raises(FetchError):
        fetch_metadata("file:///C:/secret.txt")


def test_source_names():
    assert source_name("https://www.awwwards.com/sites/x") == "Awwwards"
    assert source_name("https://blog.example.org/post") == "blog.example.org"
