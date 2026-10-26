"""Import Framework7's kitchen-sink screens (github.com/framework7io/framework7, MIT).

Framework7 builds iOS- and Android-style mobile apps from plain HTML + CSS. Its
"kitchen sink" demo has one HTML page per screen pattern:
  kitchen-sink/core/pages/<name>.html

Most pages are static markup, which the gallery renders live as phone screens using
Framework7's CSS (vendored, MIT), with an iOS / Material theme switch. Pages that rely on
template expressions (${...}) or scripts can't render without the app, so they're skipped.
"""

import re

from designlib.core.schema import Entry
from designlib.importers.common import files_under, open_repo, read_text, save_imported, title_case

PAGES = "kitchen-sink/core/pages/"
GITHUB = "https://github.com/framework7io/framework7/blob/master/" + PAGES
SKIP_PAGES = {"about", "404", "home"}


# Pages whose content is drawn by JavaScript (charts, calendars, pickers...): they'd look empty.
JS_DRAWN = {"area-chart", "calendar", "picker", "swiper-gallery", "text-editor", "home"}


def unwrap(html: str) -> str:
    """Some pages wrap static markup in a router component (<template> + <script>).
    Keep just the markup inside <template>."""
    found = re.search(r"<template>(.*)</template>", html, re.DOTALL)
    return found.group(1) if found else html


def is_static(html: str) -> bool:
    return "${" not in html and "<script" not in html and "<template" not in html


def page_title(html: str, name: str) -> str:
    found = re.search(r'<div class="title"[^>]*>\s*([^<]+?)\s*</div>', html)
    return found.group(1).strip() if found else title_case(name)


def build_entry(name: str, html: str) -> Entry | None:
    if name in SKIP_PAGES or name in JS_DRAWN or "${" in html:
        return None  # needs the running app to show anything
    html = unwrap(html)
    if not is_static(html) or 'class="page' not in html:
        return None
    title = page_title(html, name)
    return Entry(
        id=f"framework7-{name}",
        title=f"{title} (Framework7 mobile screen)",
        source="Framework7",
        url=GITHUB + f"{name}.html",
        license="MIT",
        type="screen",
        tags=[name, "framework7", "ios", "material", "mobile-app"],
        framework="html",
        notes=f"A {title.lower()} screen from Framework7's kitchen sink, shown with Framework7's iOS or "
              f"Material (Android) theme. Framework7 builds mobile apps (and PWAs / Capacitor apps) "
              f"from HTML.\n\nUse: npm i framework7, then the same markup inside a Framework7 app. "
              f"Docs: https://framework7.io/docs/",
        code=html.strip(),
    )


def run(limit: int = 0, refresh: bool = False) -> tuple[int, int]:
    entries = []
    skipped = 0
    with open_repo("framework7io", "framework7", branch="master", refresh=refresh) as (archive, prefix):
        for path in files_under(archive, prefix + PAGES, r"^[^/]+\.html$"):
            name = path.rsplit("/", 1)[1].removesuffix(".html")
            entry = build_entry(name, read_text(archive, path))
            if entry:
                entries.append(entry)
            else:
                skipped += 1
    print(f"{len(entries)} static screens ({skipped} pages need the running app and were skipped)")
    return save_imported(entries[:limit] if limit > 0 else entries)
