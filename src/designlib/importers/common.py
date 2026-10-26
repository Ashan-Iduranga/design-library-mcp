"""Shared importer plumbing: download a GitHub repo as a zip, verify its license,
and save imported entries without overwriting your own edits.

We never extract or execute anything from the downloaded zip. Importers only
read text files out of it with `zipfile`.
"""

import re
import zipfile
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

import httpx

from designlib import config
from designlib.core.fetch import USER_AGENT
from designlib.core.index import rebuild_index
from designlib.core.schema import Entry
from designlib.core.dedupe import DuplicateIndex
from designlib.core.storage import iter_entries, load_entry, save_entry

CACHE_DIR = config.PROJECT_ROOT / ".cache"

# Text that must appear in the LICENSE file for each license we accept.
LICENSE_MARKERS = {
    "MIT": ["MIT License", "Permission is hereby granted, free of charge"],
    "ISC": ["ISC License", "Permission to use, copy, modify, and/or distribute"],
    "Apache-2.0": ["Apache License", "Version 2.0"],
}

# Fields you curate by hand. A re-import keeps your values for these.
USER_FIELDS = ("my_rating", "favorite", "when_to_use", "avoid_when", "style_notes", "prompt", "local_image", "added_at")


class ImportStopped(Exception):
    """Raised when an import must not continue (e.g. the license isn't open)."""


def download_repo(owner: str, repo: str, branch: str = "main", refresh: bool = False) -> Path:
    """Download github.com/<owner>/<repo> as a zip into .cache/ (once)."""
    target = CACHE_DIR / repo / "repo.zip"
    if target.exists() and not refresh:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}"
    print(f"Downloading {url} ...")
    with httpx.stream("GET", url, headers={"User-Agent": USER_AGENT}, follow_redirects=True, timeout=120) as response:
        response.raise_for_status()
        with open(target, "wb") as file:
            for chunk in response.iter_bytes():
                file.write(chunk)
    return target


@contextmanager
def open_repo(owner: str, repo: str, license: str = "MIT", branch: str = "main", refresh: bool = False):
    """Download (once), verify the LICENSE, and open a repo zip.

        with open_repo("shadcn-ui", "ui") as (archive, prefix):
            text = read_text(archive, prefix + "README.md")
    """
    path = download_repo(owner, repo, branch=branch, refresh=refresh)
    with zipfile.ZipFile(path) as archive:
        print(f"License check passed: {verify_license(archive, license)}")
        yield archive, root_prefix(archive)


def files_under(archive: zipfile.ZipFile, folder: str, pattern: str = r".*") -> list[str]:
    """Sorted file names inside `folder` (a full zip path ending in '/') matching `pattern`."""
    return sorted(
        name for name in archive.namelist()
        if name.startswith(folder) and not name.endswith("/") and re.search(pattern, name.removeprefix(folder))
    )


def title_case(slug: str) -> str:
    """'dashboard-01' -> 'Dashboard 01'"""
    return slug.replace("-", " ").replace("_", " ").strip().title()


def root_prefix(archive: zipfile.ZipFile) -> str:
    """GitHub zips put everything inside one folder like 'hyperui-main/'."""
    return archive.namelist()[0].split("/")[0] + "/"


def verify_license(archive: zipfile.ZipFile, expected: str) -> str:
    """Check the repo's LICENSE really is the open license we expect. Returns its first line."""
    prefix = root_prefix(archive)
    candidates = [n for n in archive.namelist() if n.removeprefix(prefix).upper() in ("LICENSE", "LICENSE.MD", "LICENSE.TXT")]
    if not candidates:
        raise ImportStopped("no LICENSE file found in the repository: not importing")
    text = archive.read(candidates[0]).decode("utf-8", errors="replace")
    markers = LICENSE_MARKERS.get(expected, [])
    if not markers or not all(marker in text for marker in markers):
        raise ImportStopped(
            f"LICENSE does not look like {expected}: not importing. First line: {text.strip().splitlines()[0]!r}"
        )
    return text.strip().splitlines()[0]


def read_text(archive: zipfile.ZipFile, name: str) -> str:
    return archive.read(name).decode("utf-8", errors="replace")


def round_robin(groups: dict[str, list], limit: int) -> Iterator:
    """Take items from each group in turn, so a limited import covers every category.

    limit <= 0 means "everything".
    """
    queues = [list(items) for _, items in sorted(groups.items())]
    taken = 0
    while any(queues):
        for queue in queues:
            if queue:
                if 0 < limit <= taken:
                    return
                yield queue.pop(0)
                taken += 1


def save_imported(entries: Iterable[Entry]) -> tuple[int, int]:
    """Write entries, keeping your hand-edited fields on entries that already exist.

    Returns (created, updated). The index is rebuilt once at the end, which is
    much faster than indexing hundreds of entries one by one.
    """
    created = updated = skipped = 0
    known = DuplicateIndex(iter_entries())  # everything already in the library
    for entry in entries:
        if known.duplicate_of(entry):
            skipped += 1  # same resource is already in the library under another id
            continue
        known.add(entry)
        existing = load_entry(entry.id)
        if existing:
            for field in USER_FIELDS:
                setattr(entry, field, getattr(existing, field))
            updated += 1
        else:
            created += 1
        save_entry(entry)
    rebuild_index()
    if skipped:
        print(f"Skipped {skipped} duplicates already in the library.")
    return created, updated
