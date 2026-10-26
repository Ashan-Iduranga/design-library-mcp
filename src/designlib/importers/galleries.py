"""Import link-only references from inspiration galleries that allow it in robots.txt
and publish a sitemap: SaaS Landing Page and DesignPrompts.

For each page we keep only: URL, title, description, og:image URL (hotlinked) and
the tags the page itself declares. No page content or images are stored.
Every request goes through core.fetch, so robots.txt, the honest User-Agent and the
2-second per-site delay all apply. Pages already in the library are skipped, so an
interrupted import can simply be run again.
"""

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from designlib.core import fetch
from designlib.core.fetch import FetchError
from designlib.core.index import rebuild_index
from designlib.core.schema import LINK_ONLY, Entry, slugify
from designlib.core.storage import iter_entries, save_entry


@dataclass
class Page:
    url: str
    html: str
    meta: fetch.PageMeta


@dataclass
class Gallery:
    name: str  # source name shown in the library
    id_prefix: str
    sitemaps: list[str]
    wanted: Callable[[str], bool]  # which sitemap URLs are references we want
    build: Callable[[Page], dict]  # page -> extra Entry fields (type, tags, ...)


# ---------- SaaS Landing Page ----------

SLP_RELTAG = re.compile(r'href="https://saaslandingpage\.com/(tag|technology|font)/([^/"]+)/"\s+rel="tag"')


def slp_wanted(url: str) -> bool:
    # Landing-page posts live at /<slug>/. Everything else (templates are paid,
    # tags, fonts, articles, about...) is skipped.
    path = urlparse(url).path.strip("/")
    return bool(path) and "/" not in path and path not in {"tags", "templates", "articles", "blog", "about-us"}


def slp_build(page: Page) -> dict:
    found = SLP_RELTAG.findall(page.html)
    tags = [value for kind, value in found if kind in ("tag", "technology")]
    fonts = [value.replace("-", " ").title() for kind, value in found if kind == "font"]
    title = page.meta.title.removesuffix(" - SaaS Landing Page").removesuffix(" page").strip()
    return {
        "title": f"{title} landing page",
        "type": "screen",
        "tags": ["landing-page", "saas", *tags],
        "style_notes": {"fonts": ", ".join(fonts)},
    }


# ---------- DesignPrompts ----------


def dp_wanted(url: str) -> bool:
    parts = urlparse(url).path.strip("/").split("/")
    # /components/<style>            a whole design style
    # /components/<style>/<element>  one component in that style
    # (/components/catalogue/<style> repeats the style page, so it's skipped)
    return parts[0] == "components" and len(parts) in (2, 3) and parts[1] != "catalogue"


def dp_build(page: Page) -> dict:
    parts = urlparse(page.url).path.strip("/").split("/")
    style = parts[1]
    if len(parts) == 2:
        return {
            "title": f"{style.replace('-', ' ').title()} style (DesignPrompts)",
            "type": "style",
            "tags": [style, "designprompts", "prompt", "design-style"],
        }
    element = parts[2]
    return {
        "title": f"{element.replace('-', ' ').title()} in {style.replace('-', ' ').title()} style",
        "type": "component",
        "tags": [element, style, "designprompts", "prompt"],
    }


GALLERIES = {
    "saaslandingpage": Gallery(
        name="SaaS Landing Page",
        id_prefix="slp",
        sitemaps=["https://saaslandingpage.com/post-sitemap.xml"],
        wanted=slp_wanted,
        build=slp_build,
    ),
    "designprompts": Gallery(
        name="DesignPrompts",
        id_prefix="dp",
        sitemaps=["https://designprompts.dev/sitemap.xml"],
        wanted=dp_wanted,
        build=dp_build,
    ),
}


def sitemap_urls(sitemap: str) -> list[str]:
    response = httpx.get(sitemap, headers={"User-Agent": fetch.USER_AGENT}, timeout=30, follow_redirects=True)
    response.raise_for_status()
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", response.text)


def entry_id(prefix: str, url: str) -> str:
    path = urlparse(url).path.strip("/") or "home"
    return f"{prefix}-{slugify(path)[:40].rstrip('-')}-{hashlib.sha1(url.encode()).hexdigest()[:6]}"


def make_entry(gallery: Gallery, page: Page) -> Entry:
    fields = gallery.build(page)
    return Entry(
        id=entry_id(gallery.id_prefix, page.url),
        source=gallery.name,
        url=page.url,
        license=LINK_ONLY,
        notes=page.meta.description,
        preview_image_url=page.meta.image_url,
        **fields,
    )


def run(name: str, limit: int = 0) -> tuple[int, int, int]:
    """Import one gallery. Returns (added, skipped_existing, failed)."""
    gallery = GALLERIES[name]
    urls = [u for sitemap in gallery.sitemaps for u in sitemap_urls(sitemap) if gallery.wanted(u)]
    have = {entry.url for entry in iter_entries() if entry.source == gallery.name}
    todo = [u for u in dict.fromkeys(urls) if u not in have]
    if limit > 0:
        todo = todo[:limit]
    print(f"{gallery.name}: {len(urls)} pages in sitemap, {len(have)} already in library, {len(todo)} to fetch")
    print(f"About {len(todo) * fetch.MIN_DELAY_SECONDS / 60:.0f} minutes at one request every {fetch.MIN_DELAY_SECONDS:g} s.")

    added = failed = 0
    with httpx.Client(headers={"User-Agent": fetch.USER_AGENT}, timeout=fetch.TIMEOUT_SECONDS, follow_redirects=True) as client:
        for number, url in enumerate(todo, start=1):
            try:
                meta, html = fetch.fetch_page(url, client=client)
                save_entry(make_entry(gallery, Page(url=url, html=html, meta=meta)))
                added += 1
            except (FetchError, ValueError) as error:
                failed += 1
                print(f"  skipped {url}: {error}")
            if number % 100 == 0:
                rebuild_index()  # make progress searchable while the import runs
                print(f"  {number}/{len(todo)} done")
    rebuild_index()
    return added, len(have), failed
