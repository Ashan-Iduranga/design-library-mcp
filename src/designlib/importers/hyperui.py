"""Import Tailwind components from HyperUI (github.com/markmead/hyperui, MIT).

Repo layout we rely on:
  public/examples/<category>/<collection>/<n>.html       one example per file
  public/examples/<category>/<collection>/<n>-dark.html  dark variant (skipped by default)
  src/content/collection/<category>/<collection>.mdx     front matter with the collection
                                                          title and a `components` list whose
                                                          order matches 1.html, 2.html, ...
"""

import re
import zipfile

import yaml
from bs4 import BeautifulSoup

from designlib.core.schema import Entry
from designlib.importers.common import (
    download_repo,
    read_text,
    root_prefix,
    round_robin,
    save_imported,
    verify_license,
)

OWNER, REPO = "markmead", "hyperui"
SITE = "https://www.hyperui.dev/components"
GITHUB_BLOB = f"https://github.com/{OWNER}/{REPO}/blob/main"

# Marketing collections that are whole page sections rather than small widgets.
LAYOUT_COLLECTIONS = {
    "banners", "blog-cards", "contact-forms", "ctas", "faqs", "footers",
    "headers", "logo-clouds", "sections", "team-sections", "testimonials",
}


def read_front_matter(text: str) -> dict:
    match = re.match(r"---\n(.*?)\n---", text.replace("\r\n", "\n"), re.DOTALL)
    return yaml.safe_load(match.group(1)) if match else {}


def extract_component(html: str) -> str:
    """Keep what's inside <body>, wrapped in a div with the body's layout classes.

    The example pages rely on <body class="mx-auto max-w-3xl p-6"> for spacing,
    so we carry those classes over instead of losing them.
    """
    body = BeautifulSoup(html, "html.parser").body
    if body is None:
        return html.strip()
    inner = body.decode_contents().strip()
    classes = " ".join(c for c in body.get("class", []) if not c.startswith("dark:"))
    return f'<div class="{classes}">\n{inner}\n</div>' if classes else inner


def collect(archive: zipfile.ZipFile, include_dark: bool = False) -> dict[str, list[Entry]]:
    """Build entries grouped by collection (e.g. 'application/accordions')."""
    prefix = root_prefix(archive)
    names = archive.namelist()
    groups: dict[str, list[Entry]] = {}

    for mdx in sorted(n for n in names if re.fullmatch(rf"{prefix}src/content/collection/[^/]+/[^/]+\.mdx", n)):
        category, slug = mdx.removesuffix(".mdx").split("/")[-2:]
        meta = read_front_matter(read_text(archive, mdx))
        components = meta.get("components") or []
        collection_title = meta.get("title", slug.replace("-", " ").title())
        terms = meta.get("terms") or []

        for number, component in enumerate(components, start=1):
            variants = [("", False)] + ([("-dark", True)] if include_dark and component.get("dark") else [])
            for suffix, is_dark in variants:
                path = f"public/examples/{category}/{slug}/{number}{suffix}.html"
                if prefix + path not in names:
                    continue
                title = f"{collection_title}: {component.get('title', number)}"
                if category == "neobrutalism":
                    title += " (neobrutalism)"
                if is_dark:
                    title += " (dark)"
                tags = [category, slug, "hyperui", *terms] + (["dark"] if is_dark else [])
                entry = Entry(
                    id=f"hyperui-{category}-{slug}-{number}{suffix}",
                    title=title,
                    source="HyperUI",
                    url=f"{SITE}/{category}/{slug}",
                    license="MIT",
                    type="layout" if slug in LAYOUT_COLLECTIONS else "component",
                    tags=tags,
                    framework="tailwind",
                    notes=f"{component.get('description', '')}\n\nOriginal file: {GITHUB_BLOB}/{path}".strip(),
                    code=extract_component(read_text(archive, prefix + path)),
                )
                groups.setdefault(f"{category}/{slug}", []).append(entry)
    return groups


def run(limit: int = 60, include_dark: bool = False, refresh: bool = False) -> tuple[int, int]:
    zip_path = download_repo(OWNER, REPO, refresh=refresh)
    with zipfile.ZipFile(zip_path) as archive:
        license_line = verify_license(archive, "MIT")
        print(f"License check passed: {license_line}")
        groups = collect(archive, include_dark=include_dark)
    return save_imported(round_robin(groups, limit))
