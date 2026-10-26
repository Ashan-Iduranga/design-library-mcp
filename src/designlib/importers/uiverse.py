"""Import UI elements from Uiverse galaxy (github.com/uiverse-io/galaxy, MIT).

Repo layout we rely on:
  <Category>/<author>_<name>.html
Each file starts with a credit comment such as
  /* From Uiverse.io by 0x-Sarthak  - Tags: button, hover, rounded */
Files without a <style> block use Tailwind classes instead of CSS.
"""

import hashlib
import re
import zipfile

from designlib.core.schema import Entry, slugify
from designlib.importers.common import (
    download_repo,
    read_text,
    root_prefix,
    round_robin,
    save_imported,
    verify_license,
)

OWNER, REPO = "uiverse-io", "galaxy"
GITHUB_BLOB = f"https://github.com/{OWNER}/{REPO}/blob/main"

# Folder name -> (entry type, a clean tag for the category)
CATEGORIES = {
    "Buttons": ("component", "button"),
    "Cards": ("component", "card"),
    "Checkboxes": ("component", "checkbox"),
    "Forms": ("component", "form"),
    "Inputs": ("component", "input"),
    "Notifications": ("component", "notification"),
    "Radio-buttons": ("component", "radio"),
    "Toggle-switches": ("interaction", "toggle"),
    "Tooltips": ("interaction", "tooltip"),
    "loaders": ("interaction", "loader"),
    "Patterns": ("style", "pattern"),
}

CREDIT = re.compile(r"From Uiverse\.io by (?P<author>\S+)\s*(?:-\s*Tags:\s*(?P<tags>.*?))?\s*(?:\*/|-->)")


def parse_credit(code: str) -> tuple[str, list[str]]:
    match = CREDIT.search(code)
    if not match:
        return "", []
    tags = [t.strip().lower() for t in (match.group("tags") or "").split(",") if t.strip()]
    return match.group("author"), tags


def build_entry(path: str, code: str) -> Entry | None:
    folder, filename = path.split("/")[-2:]
    if folder not in CATEGORIES:
        return None
    entry_type, category_tag = CATEGORIES[folder]
    author, tags = parse_credit(code)
    stem = filename.removesuffix(".html")
    file_author, _, name = stem.partition("_")
    author = author or file_author
    is_tailwind = "<style" not in code or "tailwind" in tags
    short_hash = hashlib.sha1(path.encode()).hexdigest()[:6]  # keeps ids unique after slug truncation

    return Entry(
        id=f"uiverse-{slugify(stem)[:40].rstrip('-')}-{short_hash}",
        title=f"{category_tag.capitalize()} by {author} ({name or stem})",
        source="Uiverse",
        url=f"https://uiverse.io/{author}/{name}" if name else "https://uiverse.io",
        license="MIT",
        type=entry_type,
        tags=[category_tag, "uiverse", *[t for t in tags if t not in ("tailwind", "tailwindcss")][:8]],
        framework="tailwind" if is_tailwind else "html",
        notes=f"By {author} on Uiverse.io.\n\nOriginal file: {GITHUB_BLOB}/{folder}/{filename}",
        code=code.strip(),
    )


def collect(archive: zipfile.ZipFile, categories: list[str] | None = None) -> dict[str, list[Entry]]:
    prefix = root_prefix(archive)
    wanted = {c.lower() for c in categories or []}
    groups: dict[str, list[Entry]] = {}
    for name in sorted(archive.namelist()):
        if not name.endswith(".html") or name.count("/") != 2:
            continue
        folder = name.removeprefix(prefix).split("/")[0]
        if wanted and folder.lower() not in wanted and CATEGORIES.get(folder, ("", ""))[1] not in wanted:
            continue
        entry = build_entry(name.removeprefix(prefix), read_text(archive, name))
        if entry:
            groups.setdefault(folder, []).append(entry)
    return groups


def run(limit: int = 60, categories: list[str] | None = None, refresh: bool = False) -> tuple[int, int]:
    zip_path = download_repo(OWNER, REPO, refresh=refresh)
    with zipfile.ZipFile(zip_path) as archive:
        license_line = verify_license(archive, "MIT")
        print(f"License check passed: {license_line}")
        groups = collect(archive, categories)
    return save_imported(round_robin(groups, limit))
