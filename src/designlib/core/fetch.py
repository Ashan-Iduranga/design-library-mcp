"""Polite, metadata-only page fetching.

We read a page's <title>, description and og:image *URL* - nothing else.
No images are downloaded and no page content is stored.

Politeness rules:
  * robots.txt is checked first; if it disallows us, we stop.
  * Every request carries an honest User-Agent.
  * At least MIN_DELAY_SECONDS between two requests to the same host.
  * Only the first MAX_BYTES of a page are read (metadata lives in <head>).
"""

import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "design-library-mcp/0.1 (personal local design library; metadata only)"
MIN_DELAY_SECONDS = 2.0
TIMEOUT_SECONDS = 10.0
MAX_BYTES = 1_000_000

# Friendly names for sources we know. Anything else uses the hostname.
KNOWN_SOURCES = {
    "collectui.com": "Collect UI",
    "godly.website": "Godly",
    "land-book.com": "Land-book",
    "lapa.ninja": "Lapa Ninja",
    "awwwards.com": "Awwwards",
    "saaslandingpage.com": "SaaS Landing Page",
    "designprompts.dev": "DesignPrompts",
    "realtimecolors.com": "Realtime Colors",
    "hyperui.dev": "HyperUI",
    "uiverse.io": "Uiverse",
    "ui.shadcn.com": "shadcn/ui",
    "magicui.design": "Magic UI",
    "flowbite.com": "Flowbite",
    "daisyui.com": "daisyUI",
    "open-props.style": "Open Props",
    "radix-ui.com": "Radix",
    "lucide.dev": "Lucide",
    "heroicons.com": "Heroicons",
    "ui.aceternity.com": "Aceternity UI",
}


class FetchError(Exception):
    """Raised when we can't (or shouldn't) fetch a page."""


@dataclass
class PageMeta:
    url: str
    title: str = ""
    description: str = ""
    image_url: str | None = None
    source: str = ""


_last_request: dict[str, float] = {}  # host -> time of our last request


def _wait_for_turn(host: str) -> None:
    elapsed = time.monotonic() - _last_request.get(host, -1e9)
    if elapsed < MIN_DELAY_SECONDS:
        time.sleep(MIN_DELAY_SECONDS - elapsed)
    _last_request[host] = time.monotonic()


def source_name(url: str) -> str:
    host = (urlparse(url).hostname or "").removeprefix("www.")
    for domain, name in KNOWN_SOURCES.items():
        if host == domain or host.endswith("." + domain):
            return name
    return host


def _robots_allows(client: httpx.Client, url: str) -> bool:
    parts = urlparse(url)
    robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
    _wait_for_turn(parts.netloc)
    try:
        response = client.get(robots_url)
    except httpx.HTTPError:
        return True  # no robots.txt reachable -> no rules to follow
    if response.status_code >= 400:
        return True  # same convention as Python's robotparser: missing file = allowed
    parser = RobotFileParser()
    parser.parse(response.text.splitlines())
    return parser.can_fetch(USER_AGENT, url)


def _read_limited(client: httpx.Client, url: str) -> tuple[str, str]:
    """GET the page but stop after MAX_BYTES. Returns (final_url, html)."""
    with client.stream("GET", url) as response:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "html" not in content_type:
            raise FetchError(f"not an HTML page (content-type: {content_type or 'unknown'})")
        chunks, size = [], 0
        for chunk in response.iter_bytes():
            chunks.append(chunk)
            size += len(chunk)
            if size >= MAX_BYTES:
                break
        encoding = response.encoding or "utf-8"
        return str(response.url), b"".join(chunks).decode(encoding, errors="replace")


def parse_meta(html: str, page_url: str) -> PageMeta:
    soup = BeautifulSoup(html, "html.parser")

    def meta(*names: str) -> str:
        for name in names:
            tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
            if tag and tag.get("content"):
                return " ".join(tag["content"].split())
        return ""

    title = meta("og:title", "twitter:title")
    if not title and soup.title and soup.title.string:
        title = " ".join(soup.title.string.split())
    image = meta("og:image", "og:image:url", "twitter:image")

    return PageMeta(
        url=page_url,
        title=title,
        description=meta("og:description", "description", "twitter:description"),
        # og:image is sometimes relative ("/og.png"), so resolve it against the page URL
        image_url=urljoin(page_url, image) if image else None,
        source=source_name(page_url),
    )


def fetch_metadata(url: str, client: httpx.Client | None = None) -> PageMeta:
    """Fetch title/description/og:image URL for one page, politely."""
    if urlparse(url).scheme not in ("http", "https"):
        raise FetchError("only http(s) URLs are supported")

    own_client = client is None
    if own_client:
        client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT_SECONDS,
            follow_redirects=True,
        )
    try:
        if not _robots_allows(client, url):
            raise FetchError("robots.txt does not allow fetching this page")
        _wait_for_turn(urlparse(url).netloc)
        final_url, html = _read_limited(client, url)
        return parse_meta(html, final_url)
    except httpx.HTTPError as error:
        raise FetchError(f"could not fetch {url}: {error}") from error
    finally:
        if own_client:
            client.close()
