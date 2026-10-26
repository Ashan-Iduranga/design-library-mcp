"""Import official mobile design guidelines and UI kits as link-only references.

  Material Design 3   m3.material.io: component overviews, foundations and styles, found via
                      its sitemap (robots.txt allows it); title, description and preview image.
  Apple HIG           developer.apple.com/design/human-interface-guidelines: every page, found
                      through Apple's own documentation index (JSON).
  Apple UI kits       the Figma kits linked on developer.apple.com/design/resources.
  Wear OS kits        the two official Figma kits (apps, tiles).
  MD3 Sketch kit      a free community Sketch port of Material 3 (by Hxly).

Everything goes through core.fetch's politeness rules (robots.txt, honest User-Agent,
2 s between requests to a site). Only links, titles and descriptions are kept.
"""

import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from designlib.core import fetch
from designlib.core.fetch import FetchError
from designlib.core.schema import LINK_ONLY, Entry, slugify
from designlib.importers.common import save_imported, title_case
from designlib.importers.galleries import sitemap_urls

M3_SITEMAP = "https://m3.material.io/sitemap.xml"
HIG_INDEX = "https://developer.apple.com/tutorials/data/design/human-interface-guidelines.json"
HIG_PREFIX = "/design/human-interface-guidelines/"
APPLE_RESOURCES = "https://developer.apple.com/design/resources/"
MAX_HIG_PAGES = 300

PLATFORM_WORDS = {"ios": "ios", "ipados": "ipados", "watchos": "watchos", "macos": "macos",
                  "tvos": "tvos", "visionos": "visionos"}


def _client() -> httpx.Client:
    return httpx.Client(headers={"User-Agent": fetch.USER_AGENT}, timeout=fetch.TIMEOUT_SECONDS, follow_redirects=True)


def get_json(client: httpx.Client, url: str) -> dict:
    """A polite JSON request: robots.txt checked, one request per 2 s per site."""
    if not fetch._robots_allows(client, url):
        raise FetchError(f"robots.txt does not allow {url}")
    fetch._wait_for_turn(urlparse(url).netloc)
    response = client.get(url)
    response.raise_for_status()
    return response.json()


# ---------- Material Design 3 ----------


def m3_wanted(url: str) -> bool:
    parts = urlparse(url).path.strip("/").split("/")
    if parts[0] == "components":
        return len(parts) == 3 and parts[2] == "overview"
    if parts[0] in ("foundations", "styles"):
        return len(parts) == 2 or (len(parts) == 3 and parts[2] == "overview")
    return False


def m3_entries(client: httpx.Client, limit: int = 0) -> list[Entry]:
    urls = [u for u in sitemap_urls(M3_SITEMAP) if m3_wanted(u)]
    entries = []
    for url in urls[: limit or None]:
        try:
            meta, _ = fetch.fetch_page(url, client=client)
        except FetchError as error:
            print(f"  skipped {url}: {error}")
            continue
        parts = urlparse(url).path.strip("/").split("/")
        section, topic = parts[0], parts[1]
        title = re.sub(r"\s+[–-]\s+Material Design 3$", "", meta.title) or title_case(topic)
        entries.append(Entry(
            id=f"m3-{section}-{slugify(topic)}",
            title=f"Material 3: {title}",
            source="Material Design 3",
            url=url,
            license=LINK_ONLY,
            type="style" if section != "components" else "component",
            tags=[slugify(topic), "material-3", "guidelines", "android", section],
            notes=meta.description + "\n\nOfficial Material Design 3 guidelines (Google): usage, anatomy, "
                  "specs and accessibility. Use with Jetpack Compose, Flutter or @material/web.",
            preview_image_url=meta.image_url,
        ))
    return entries


# ---------- Apple Human Interface Guidelines ----------


def _abstract(reference: dict) -> str:
    return " ".join(part.get("text", "") for part in reference.get("abstract", []) if part.get("type") == "text").strip()


def hig_entries(client: httpx.Client, limit: int = 0) -> list[Entry]:
    """Walk Apple's documentation index: every page lists its child pages as references."""
    found: dict[str, dict] = {}
    queue = [HIG_INDEX]
    visited = set()
    while queue and len(visited) < MAX_HIG_PAGES and (not limit or len(found) < limit):
        json_url = queue.pop(0)
        if json_url in visited:
            continue
        visited.add(json_url)
        try:
            data = get_json(client, json_url)
        except (FetchError, httpx.HTTPError, ValueError) as error:
            print(f"  skipped {json_url}: {error}")
            continue
        for ref in data.get("references", {}).values():
            path = ref.get("url") or ""
            if ref.get("type") == "topic" and path.startswith(HIG_PREFIX) and path not in found:
                found[path] = ref
                queue.append("https://developer.apple.com/tutorials/data" + path.rstrip("/") + ".json")

    entries = []
    for path, ref in list(found.items())[: limit or None]:
        topic = path.removeprefix(HIG_PREFIX).strip("/")
        title = ref.get("title") or title_case(topic.split("/")[-1])
        entries.append(Entry(
            id=f"apple-hig-{slugify(topic)[:50].rstrip('-')}",
            title=f"Apple HIG: {title}",
            source="Apple HIG",
            url="https://developer.apple.com" + path,
            license=LINK_ONLY,
            type="style",
            tags=[slugify(title), "guidelines", "human-interface-guidelines", "ios", "apple"],
            notes=f"{_abstract(ref)}\n\nApple Human Interface Guidelines: how this should look and behave on "
                  f"iPhone, iPad, Mac, Apple Watch, Apple TV and Vision Pro.",
        ))
    return entries


# ---------- UI kits (Apple, Wear OS, community) ----------


def apple_kit_entries(client: httpx.Client) -> list[Entry]:
    """The Figma kits on Apple's design resources page, named after their section heading."""
    _, html = fetch.fetch_page(APPLE_RESOURCES, client=client)
    soup = BeautifulSoup(html, "html.parser")
    entries, seen = [], set()
    for link in soup.select('a[href*="figma.com/community/file/"]'):
        href = urljoin(APPLE_RESOURCES, link["href"])
        if href in seen:
            continue
        seen.add(href)
        heading = link.find_previous(["h3", "h4", "h2"])
        name = " ".join((heading.get_text() if heading else link.get_text()).split()) or "Apple design kit"
        platforms = [w for w in PLATFORM_WORDS if w in name.lower()]
        entries.append(Entry(
            id=f"apple-kit-{slugify(name)[:50].rstrip('-')}",
            title=f"Apple: {name} (Figma)",
            source="Apple Design Resources",
            url=href,
            license=LINK_ONLY,
            type="style",
            tags=[slugify(name), "ui-kit", "figma", "apple", *platforms],
            notes=f"Official Apple {name} for Figma (also on Sketch). From {APPLE_RESOURCES}. "
                  f"Apple's terms apply; use it to design apps for Apple platforms.",
        ))
    return entries


STATIC_KITS = [
    Entry(
        id="wear-os-design-kit-apps",
        title="Wear OS design kit for apps (Figma, Material 3 Expressive)",
        source="Android Developers",
        url="https://www.figma.com/community/file/1506418396052412186",
        license=LINK_ONLY,
        type="style",
        tags=["wear-os", "ui-kit", "figma", "material-3", "android", "watch"],
        notes="Official Google kit: components, styles, variables and layouts for Wear OS apps. "
              "From https://developer.android.com/design/ui/wear/guides/get-started/design-kits",
    ),
    Entry(
        id="wear-os-design-kit-tiles",
        title="Wear OS design kit for tiles (Figma, Material 3 Expressive)",
        source="Android Developers",
        url="https://www.figma.com/community/file/1507852095734722321",
        license=LINK_ONLY,
        type="style",
        tags=["wear-os", "ui-kit", "figma", "material-3", "android", "tiles"],
        notes="Official Google kit: components, styles and layouts for Wear OS tiles. "
              "From https://developer.android.com/design/ui/wear/guides/get-started/design-kits",
    ),
    Entry(
        id="md3-sketch-kit-hxly",
        title="Material Design 3 UI Kit for Sketch (Hxly, free)",
        source="Sketch App Sources",
        url="https://www.sketchappsources.com/free-source/4784-md3-material-design-3-ui-kit-sketch-freebie-resource.html",
        license=LINK_ONLY,
        type="style",
        tags=["material-3", "ui-kit", "sketch", "android"],
        notes="Free community Sketch version of Google's Material 3 kit: all MD3 components with states and "
              "variants. No license is stated, so it's kept as a link.",
    ),
]


def run(limit: int = 0, refresh: bool = False) -> tuple[int, int]:
    with _client() as client:
        print("Material Design 3 pages...")
        entries = m3_entries(client, limit)
        print("Apple Human Interface Guidelines pages...")
        entries += hig_entries(client, limit)
        print("Apple UI kits...")
        entries += apple_kit_entries(client)
    entries += STATIC_KITS
    print(f"{len(entries)} guideline pages and kits")
    return save_imported(entries)
