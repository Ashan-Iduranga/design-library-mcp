"""Querying the index. Used by the CLI, the gallery and the MCP tools."""

import re
from contextlib import closing
from dataclasses import dataclass

from designlib.core.index import connect
from designlib.core.schema import Entry

SORTS = ("relevance", "newest", "rating", "title")

# bm25() weights per FTS column: title, tags, source, notes, usage, code.
# A match in the title counts most, a match buried in code counts least.
BM25_WEIGHTS = "10.0, 6.0, 2.0, 3.0, 2.0, 0.5"


@dataclass
class Filters:
    query: str = ""
    type: str | None = None
    tags: list[str] | None = None
    framework: str | None = None
    source: str | None = None
    favorites_only: bool = False
    sort: str = "relevance"
    limit: int = 60


def to_fts_query(text: str) -> str:
    """Turn free text into a safe FTS5 query.

    Raw user text can contain FTS syntax (quotes, '-', ':', 'OR') that would
    raise errors, so we keep only word characters and quote each word.
    The trailing * makes it a prefix match, so typing "butt" already finds
    "button" while the search box updates live.
    """
    words = re.findall(r"\w+", text.lower())
    return " ".join(f'"{word}"*' for word in words)


def search(filters: Filters) -> list[Entry]:
    where: list[str] = []
    params: list = []

    fts = to_fts_query(filters.query)
    if fts:
        where.append("e.id IN (SELECT id FROM entries_fts WHERE entries_fts MATCH ?)")
        params.append(fts)
    if filters.type:
        where.append("e.type = ?")
        params.append(filters.type)
    if filters.framework:
        where.append("e.framework = ?")
        params.append(filters.framework)
    if filters.source:
        where.append("e.source = ?")
        params.append(filters.source)
    if filters.favorites_only:
        where.append("e.favorite = 1")
    for tag in filters.tags or []:  # every selected tag must be present (AND)
        where.append("EXISTS (SELECT 1 FROM entry_tags t WHERE t.entry_id = e.id AND t.tag = ?)")
        params.append(tag.strip().lower())

    sort = filters.sort if filters.sort in SORTS else "relevance"
    if sort == "relevance" and fts:
        # Join the FTS table again to get a rank for ordering.
        select = (
            f"SELECT e.data FROM entries e "
            f"JOIN (SELECT id, bm25(entries_fts, {BM25_WEIGHTS}) AS rank "
            f"      FROM entries_fts WHERE entries_fts MATCH ?) r ON r.id = e.id"
        )
        params.insert(0, fts)
        order = "r.rank ASC"  # lower bm25 = better match
    else:
        select = "SELECT e.data FROM entries e"
        order = {
            "relevance": "e.favorite DESC, e.my_rating DESC, e.added_at DESC",
            "newest": "e.added_at DESC",
            "rating": "e.my_rating DESC, e.added_at DESC",
            "title": "e.title COLLATE NOCASE ASC",
        }[sort]

    sql = select
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY {order} LIMIT ?"
    params.append(max(1, filters.limit))

    with closing(connect()) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [Entry.model_validate_json(row["data"]) for row in rows]


def get_entry(entry_id: str) -> Entry | None:
    with closing(connect()) as conn:
        row = conn.execute("SELECT data FROM entries WHERE id = ?", (entry_id,)).fetchone()
    return Entry.model_validate_json(row["data"]) if row else None


def _counts(sql: str) -> list[tuple[str, int]]:
    with closing(connect()) as conn:
        return [(row[0], row[1]) for row in conn.execute(sql).fetchall()]


def list_tags() -> list[tuple[str, int]]:
    """All tags with how many entries use each, most used first."""
    return _counts("SELECT tag, COUNT(*) FROM entry_tags GROUP BY tag ORDER BY COUNT(*) DESC, tag")


def list_sources() -> list[tuple[str, int]]:
    return _counts(
        "SELECT source, COUNT(*) FROM entries WHERE source != '' "
        "GROUP BY source ORDER BY COUNT(*) DESC, source"
    )


def list_types() -> list[tuple[str, int]]:
    return _counts("SELECT type, COUNT(*) FROM entries GROUP BY type ORDER BY COUNT(*) DESC")


def list_frameworks() -> list[tuple[str, int]]:
    return _counts("SELECT framework, COUNT(*) FROM entries GROUP BY framework ORDER BY COUNT(*) DESC")


def count_entries() -> int:
    with closing(connect()) as conn:
        return conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
