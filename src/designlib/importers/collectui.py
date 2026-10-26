"""Import Collect UI's designs as link-only references.

Collect UI has no public API or sitemap; its website reads its catalogue from its
own Supabase backend using a public "anon" key embedded in the site's JavaScript.
You chose (26 Oct 2026) to import the full catalogue that way, for personal use.
To keep it light and honest:

  * the key is read from collectui.com at run time, never stored in this repo;
  * only the columns we keep are requested, 200 designs per request, 2 s apart
    (about 20 requests for the whole catalogue);
  * we store metadata only: title, designer, categories, a link to the designer's
    original post, and the thumbnail URL (hotlinked). No images or videos are copied.
"""

import base64
import json
import re
import time

import httpx

from designlib.core.fetch import MIN_DELAY_SECONDS, USER_AGENT
from designlib.core.index import rebuild_index
from designlib.core.schema import LINK_ONLY, Entry, slugify
from designlib.core.storage import load_entry, save_entry
from designlib.importers.common import ImportStopped

SITE = "https://collectui.com"
PAGE_SIZE = 200
COLUMNS = "id,title,source_url,media_url,media_type,thumbnail,categories,designer_username,published_at"
USER_FIELDS = ("my_rating", "favorite", "when_to_use", "avoid_when", "style_notes", "prompt", "local_image", "notes")

# Collect UI category -> our entry type. Anything not listed is a "screen".
INTERACTION = {"ui-interaction", "hover-state", "scroll-transition", "micro-interaction", "animation",
               "funny-animation", "character-animation", "loading", "loader", "transition", "range-slider",
               "toggle", "button", "dial-pad", "verification-code", "motion"}
PALETTE = {"color-palette", "color", "colors", "gradient"}
STYLE = {"branding", "logo", "illustration", "style-guide", "brutal-design", "typography", "3d", "icons",
         "book-cover", "business-card", "stamp", "playing-cards"}
LAYOUT = {"landing-page", "landing-pages", "hero-section", "footer", "navigation", "features", "cta",
          "pricing", "about-us", "portfolio", "agency", "ai-sites", "framer"}


def _get(client: httpx.Client, url: str, **kwargs) -> httpx.Response:
    time.sleep(MIN_DELAY_SECONDS)  # one request at a time, with a pause
    response = client.get(url, **kwargs)
    response.raise_for_status()
    return response


def find_backend(client: httpx.Client) -> tuple[str, str]:
    """Read the public Supabase URL + anon key from collectui.com's own JavaScript."""
    home = _get(client, SITE + "/").text
    # The page loads its code as "./_app/immutable/....js" (or "/_app/...").
    scripts = list(dict.fromkeys(re.findall(r'["\'](?:\.?/)?(_app/immutable/[^"\']+\.js)["\']', home)))
    pending = [f"{SITE}/{path}" for path in scripts]
    seen = set()
    while pending and len(seen) < 40:
        url = pending.pop(0)
        if url in seen:
            continue
        seen.add(url)
        js = _get(client, url).text
        for token in re.findall(r"eyJ[\w-]+\.eyJ[\w-]+\.[\w-]+", js):
            claims = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "=="))
            if claims.get("role") == "anon" and claims.get("ref"):
                return f"https://{claims['ref']}.supabase.co", token
        # follow imports to other chunks of the app
        for chunk in re.findall(r'["\'](\.{1,2}/[^"\']+\.js)["\']', js):
            pending.append(httpx.URL(url).join(chunk).__str__())
    raise ImportStopped("couldn't find Collect UI's public data key; the site may have changed")


def entry_type(categories: list[str]) -> str:
    cats = set(categories)
    if cats & PALETTE:
        return "palette"
    if cats & INTERACTION:
        return "interaction"
    if cats & STYLE:
        return "style"
    if cats & LAYOUT:
        return "layout"
    return "screen"


def make_entry(post: dict, names: dict[str, str]) -> Entry | None:
    if not post.get("source_url"):
        return None
    categories = [c for c in (post.get("categories") or []) if c and not c.isdigit()]
    designer = post.get("designer_username") or "unknown"
    raw_title = " ".join((post.get("title") or "").split())
    label = ", ".join(names.get(c, c.replace("-", " ").title()) for c in categories[:2]) or "Design"
    title = f"{label} by @{designer}" + (f": {raw_title[:70]}" if raw_title else "")
    image = post.get("thumbnail") if post.get("media_type") == "video" else post.get("media_url")
    return Entry(
        id=f"collectui-{slugify(designer)[:24].rstrip('-')}-{post['id'][:8]}",
        title=title,
        source="Collect UI",
        url=post["source_url"],  # the designer's original post
        license=LINK_ONLY,
        type=entry_type(categories),
        tags=[*categories, "collectui", post.get("media_type") or ""],
        notes=f"{raw_title}\n\nDesigner: @{designer}. Curated on Collect UI ({SITE}).".strip(),
        preview_image_url=image or None,
    )


def run(limit: int = 0) -> tuple[int, int]:
    """Returns (created, updated)."""
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30, follow_redirects=True) as client:
        base, key = find_backend(client)
        headers = {"apikey": key, "Authorization": f"Bearer {key}"}
        names = {c["slug"]: c["name"] for c in _get(
            client, f"{base}/rest/v1/collectui_categories", params={"select": "slug,name"}, headers=headers
        ).json()}

        posts: list[dict] = []
        while limit <= 0 or len(posts) < limit:
            page = _get(client, f"{base}/rest/v1/collectui_posts", headers=headers, params={
                "select": COLUMNS,
                "status": "eq.Published",
                "order": "published_at.desc,id.desc",
                "offset": len(posts),
                "limit": PAGE_SIZE,
            }).json()
            posts.extend(page)
            print(f"  {len(posts)} designs read")
            if len(page) < PAGE_SIZE:
                break
    if limit > 0:
        posts = posts[:limit]

    created = updated = 0
    for post in posts:
        entry = make_entry(post, names)
        if entry is None:
            continue
        existing = load_entry(entry.id)
        if existing:  # keep your own edits on re-import
            for field in USER_FIELDS:
                setattr(entry, field, getattr(existing, field))
            entry.added_at = existing.added_at
            updated += 1
        else:
            created += 1
        save_entry(entry)
    rebuild_index()
    return created, updated
