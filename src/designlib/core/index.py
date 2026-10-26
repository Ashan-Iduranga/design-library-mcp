"""The SQLite search index (library/index.db).

Three tables:
  entries      one row per entry: columns for filtering/sorting + the full JSON
  entry_tags   one row per (entry, tag) pair, for tag filters and tag counts
  entries_fts  an FTS5 full-text table for ranked keyword search

The index is a cache. Delete index.db at any time and `rebuild_index()` will
recreate it from the JSON files.
"""

import sqlite3
from contextlib import closing

from designlib import config
from designlib.core import semantic, storage
from designlib.core.schema import Entry

# Bump this when the tables below change. An index with an older version is
# dropped and rebuilt from the JSON files automatically (it's only a cache).
SCHEMA_VERSION = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    source      TEXT,
    url         TEXT,
    license     TEXT,
    type        TEXT,
    framework   TEXT,
    my_rating   INTEGER,
    favorite    INTEGER,
    added_at    TEXT,
    updated_at  TEXT,
    text_hash   TEXT,                  -- fingerprint of the descriptive text (for semantic search)
    data        TEXT NOT NULL          -- the full entry as JSON
);

CREATE TABLE IF NOT EXISTS entry_tags (
    entry_id TEXT NOT NULL,
    tag      TEXT NOT NULL,
    PRIMARY KEY (entry_id, tag)
);

-- 'porter' stemming lets "buttons" match "button".
CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
    id UNINDEXED,
    title, tags, source, notes, usage, code,
    tokenize = 'porter unicode61 remove_diacritics 2'
);
"""


def connect() -> sqlite3.Connection:
    """Open the index, creating (and filling) it if it's missing or out of date."""
    path = config.index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row  # rows behave like dicts: row["title"]
    # A brand-new file has user_version 0, so it is filled here too.
    if conn.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
        conn.executescript("DROP TABLE IF EXISTS entries; DROP TABLE IF EXISTS entry_tags; DROP TABLE IF EXISTS entries_fts;")
        conn.executescript(SCHEMA)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        _fill(conn)
    return conn


def _fill(conn: sqlite3.Connection) -> int:
    count = 0
    for entry in storage.iter_entries():
        _insert(conn, entry)
        count += 1
    conn.commit()
    return count


def _insert(conn: sqlite3.Connection, entry: Entry) -> None:
    conn.execute(
        """INSERT INTO entries
           (id, title, source, url, license, type, framework, my_rating, favorite,
            added_at, updated_at, text_hash, data)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            entry.id,
            entry.title,
            entry.source,
            entry.url,
            entry.license,
            entry.type.value,
            entry.framework.value,
            entry.my_rating,
            int(entry.favorite),
            entry.added_at.isoformat(),
            entry.updated_at.isoformat(),
            semantic.text_hash(entry),
            entry.model_dump_json(),
        ),
    )
    conn.executemany(
        "INSERT INTO entry_tags (entry_id, tag) VALUES (?, ?)",
        [(entry.id, tag) for tag in entry.tags],
    )
    conn.execute(
        """INSERT INTO entries_fts (id, title, tags, source, notes, usage, code)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            entry.id,
            entry.title,
            " ".join(entry.tags),
            entry.source,
            f"{entry.style_notes.as_text()} {entry.notes}",
            f"{entry.when_to_use} {entry.avoid_when} {entry.prompt or ''}",
            entry.code or "",
        ),
    )


def _delete(conn: sqlite3.Connection, entry_id: str) -> None:
    conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    conn.execute("DELETE FROM entry_tags WHERE entry_id = ?", (entry_id,))
    conn.execute("DELETE FROM entries_fts WHERE id = ?", (entry_id,))


def rebuild_index() -> int:
    """Drop everything and re-read all JSON files. Returns the entry count."""
    with closing(connect()) as conn:
        conn.executescript("DELETE FROM entries; DELETE FROM entry_tags; DELETE FROM entries_fts;")
        return _fill(conn)


def index_entry(entry: Entry) -> None:
    """Add or replace one entry in the index (call after saving its JSON)."""
    with closing(connect()) as conn:
        _delete(conn, entry.id)
        _insert(conn, entry)
        conn.commit()


def unindex_entry(entry_id: str) -> None:
    with closing(connect()) as conn:
        _delete(conn, entry_id)
        conn.commit()


def save_and_index(entry: Entry, touch: bool = True) -> Entry:
    """The one way to persist an entry: JSON file first, then the index."""
    storage.save_entry(entry, touch=touch)
    index_entry(entry)
    return entry


def delete_and_unindex(entry_id: str) -> bool:
    removed = storage.delete_entry(entry_id)
    unindex_entry(entry_id)
    return removed
