"""Finding and merging duplicate references.

Two entries are the same resource when they have the same *link* AND the same *content*:

  * link     the URL without scheme, "www.", query, #fragment or trailing slash
  * content  the code (whitespace-insensitive) if there is any, else the preview image URL

Same link alone is NOT a duplicate: code libraries give many different examples the same
docs URL, and one Collect UI post can carry several different images. Identical code under
two different links (a library showing one snippet on two docs pages) IS a duplicate.
"""

import hashlib
import re
from collections import defaultdict

from designlib.core.schema import Entry


def normalise_url(url: str | None) -> str:
    url = (url or "").strip().lower()
    url = re.sub(r"^[a-z]+://", "", url)
    url = re.sub(r"^www\.", "", url)
    return url.split("#")[0].split("?")[0].rstrip("/")


def code_hash(entry: Entry) -> str | None:
    code = re.sub(r"\s+", " ", entry.code or "").strip()
    code = re.sub(r"\s*([<>])\s*", r"\1", code)  # "<b> same </b>" == "<b>same</b>"
    return hashlib.sha1(code.encode()).hexdigest() if code else None


def fingerprints(entry: Entry) -> list[str]:
    """Keys that identify this resource. Any shared key means "same resource"."""
    keys = []
    digest = code_hash(entry)
    if digest:
        keys.append("code:" + digest)
    elif entry.url or entry.preview_image_url:
        keys.append(f"link:{normalise_url(entry.url)}|img:{normalise_url(entry.preview_image_url)}")
    return keys


class DuplicateIndex:
    """Remembers fingerprints so importers can skip what the library already has."""

    def __init__(self, entries=()):
        self.owner: dict[str, str] = {}  # fingerprint -> entry id
        for entry in entries:
            self.add(entry)

    def add(self, entry: Entry) -> None:
        for key in fingerprints(entry):
            self.owner.setdefault(key, entry.id)

    def duplicate_of(self, entry: Entry) -> str | None:
        """The id of an existing *different* entry with the same resource, if any."""
        for key in fingerprints(entry):
            other = self.owner.get(key)
            if other and other != entry.id:
                return other
        return None


def find_groups(entries: list[Entry]) -> list[list[Entry]]:
    """Groups of 2+ entries that are the same resource."""
    by_key: dict[str, list[Entry]] = defaultdict(list)
    for entry in entries:
        for key in fingerprints(entry):
            by_key[key].append(entry)
    seen: set[str] = set()
    groups = []
    for members in by_key.values():
        if len(members) > 1 and members[0].id not in seen:
            seen.update(e.id for e in members)
            groups.append(members)
    return groups


def merge(group: list[Entry]) -> tuple[Entry, list[Entry]]:
    """Keep the entry you've touched most (manual categories, favorite, rating, notes),
    fold the others' tags and categories into it. Returns (kept, removed)."""
    def care(e: Entry):
        return (e.categories_manual, e.favorite, e.my_rating, bool(e.when_to_use or e.avoid_when), e.added_at)

    keep = sorted(group, key=care, reverse=True)[0]
    removed = [e for e in group if e.id != keep.id]
    for other in removed:
        keep.tags = list(dict.fromkeys([*keep.tags, *other.tags]))
        if not keep.categories_manual:
            merged = list(dict.fromkeys([*keep.categories, *other.categories]))
            keep.categories = [c for c in merged if c != "other"][:3] or ["other"]
        keep.favorite = keep.favorite or other.favorite
        keep.my_rating = max(keep.my_rating, other.my_rating)
    return keep, removed
