"""Querying the index. Used by the CLI, the gallery and the MCP tools.

Two kinds of matching:
  keyword  SQLite FTS5: entries that contain the words you typed (always available)
  hybrid   keyword results merged with semantic results (entries close in *meaning*),
           when the optional semantic extra is installed. See core/semantic.py.
"""

import re
import sys
from contextlib import closing
from dataclasses import dataclass, replace

from designlib.core import semantic
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
    platform: str | None = None  # web / mobile / desktop / any
    categories: list[str] | None = None  # match ANY of these category slugs
    favorites_only: bool = False
    sort: str = "relevance"
    limit: int = 60
    offset: int = 0  # skip this many results (for "Show more" paging)
    mode: str = "hybrid"  # "hybrid" (keyword + meaning) or "keyword"
    wait_for_model: bool = True  # False: use keyword search until the model has loaded


# Reciprocal Rank Fusion constant. Each list contributes 1 / (RRF_K + rank), so an
# entry ranked well by *both* keyword and meaning search rises to the top.
RRF_K = 60
CANDIDATES = 200  # how many results each method contributes before merging


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
    """The search everyone uses. Hybrid when possible, keyword otherwise."""
    if uses_meaning(filters):
        try:
            ranked = _hybrid_ranked(filters)
            return ranked[filters.offset : filters.offset + max(1, filters.limit)]
        except Exception as error:  # semantic search is a bonus; never break search over it
            print(f"[designlib] semantic search failed, using keywords only: {error}", file=sys.stderr)
    return keyword_search(filters)


def count_matches(filters: Filters) -> int:
    """How many entries match in total (ignores limit/offset). Used for "60 of 1,234"."""
    if uses_meaning(filters):
        try:
            return len(_hybrid_ranked(filters))
        except Exception:
            pass  # search() already reports the failure; fall back to the keyword count
    where, params, _ = _conditions(filters)
    sql = "SELECT COUNT(*) FROM entries e" + (" WHERE " + " AND ".join(where) if where else "")
    with closing(connect()) as conn:
        return conn.execute(sql, params).fetchone()[0]


def uses_meaning(filters: Filters) -> bool:
    return (
        bool(filters.query.strip())
        and filters.mode == "hybrid"
        and semantic.enabled()
        and (filters.wait_for_model or semantic.ready())
    )


def _hybrid_ranked(filters: Filters) -> list[Entry]:
    """Every hybrid match, best first (at most 2 x CANDIDATES)."""
    by_keyword = keyword_search(replace(filters, sort="relevance", limit=CANDIDATES, offset=0))
    meaning_ids = semantic.nearest(filters.query, k=CANDIDATES)
    # Apply the same type/tag/framework/... filters to the meaning results.
    by_meaning = keyword_search(replace(filters, query="", limit=CANDIDATES, offset=0), only_ids=meaning_ids)
    meaning_rank = {entry_id: rank for rank, entry_id in enumerate(meaning_ids)}
    by_meaning.sort(key=lambda entry: meaning_rank[entry.id])

    scores: dict[str, float] = {}
    entries: dict[str, Entry] = {}
    for ranked in (by_keyword, by_meaning):
        for rank, entry in enumerate(ranked):
            scores[entry.id] = scores.get(entry.id, 0.0) + 1.0 / (RRF_K + rank + 1)
            entries[entry.id] = entry

    results = sorted(entries.values(), key=lambda entry: scores[entry.id], reverse=True)
    if filters.sort == "newest":
        results.sort(key=lambda e: e.added_at, reverse=True)
    elif filters.sort == "rating":
        results.sort(key=lambda e: (e.my_rating, e.added_at), reverse=True)
    elif filters.sort == "title":
        results.sort(key=lambda e: e.title.lower())
    return results


def _conditions(filters: Filters, only_ids: list[str] | None = None) -> tuple[list[str], list, str]:
    """The WHERE clauses + parameters for the filters. Returns (where, params, fts query)."""
    where: list[str] = []
    params: list = []

    if only_ids is not None:
        where.append(f"e.id IN ({', '.join('?' * len(only_ids))})" if only_ids else "0")
        params.extend(only_ids)

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
    if filters.platform:
        where.append("e.platform = ?")
        params.append(filters.platform)
    if filters.categories:
        marks = ", ".join("?" * len(filters.categories))
        where.append(f"EXISTS (SELECT 1 FROM entry_categories c WHERE c.entry_id = e.id AND c.category IN ({marks}))")
        params.extend(filters.categories)
    if filters.favorites_only:
        where.append("e.favorite = 1")
    for tag in filters.tags or []:  # every selected tag must be present (AND)
        where.append("EXISTS (SELECT 1 FROM entry_tags t WHERE t.entry_id = e.id AND t.tag = ?)")
        params.append(tag.strip().lower())
    return where, params, fts


def keyword_search(filters: Filters, only_ids: list[str] | None = None) -> list[Entry]:
    """Plain SQL + FTS5 search. `only_ids` restricts results to those entries."""
    if only_ids is not None and not only_ids:
        return []
    where, params, fts = _conditions(filters, only_ids)

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
    sql += f" ORDER BY {order} LIMIT ? OFFSET ?"
    params.extend([max(1, filters.limit), max(0, filters.offset)])

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


def category_counts(filters: Filters) -> dict[str, int]:
    """How many entries are in each category, for the current platform and filters
    (but not the current category, so the sidebar still shows every option)."""
    where, params, _ = _conditions(replace(filters, query="", categories=None))
    sql = "SELECT c.category, COUNT(*) FROM entry_categories c JOIN entries e ON e.id = c.entry_id"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " GROUP BY c.category"
    with closing(connect()) as conn:
        return dict(conn.execute(sql, params).fetchall())


def platform_counts(filters: Filters) -> dict[str, int]:
    """Entries per platform for the current category and filters (for the platform tabs)."""
    where, params, _ = _conditions(replace(filters, query="", platform=None))
    sql = "SELECT e.platform, COUNT(*) FROM entries e"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " GROUP BY e.platform"
    with closing(connect()) as conn:
        return dict(conn.execute(sql, params).fetchall())


def list_frameworks() -> list[tuple[str, int]]:
    return _counts("SELECT framework, COUNT(*) FROM entries GROUP BY framework ORDER BY COUNT(*) DESC")


def count_entries() -> int:
    with closing(connect()) as conn:
        return conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
