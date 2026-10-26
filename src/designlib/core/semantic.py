"""Optional semantic search: find entries by meaning, not just shared words.

"calm" can match an entry described as "quiet, minimal" even though no word
is shared. How it works:

  1. Each entry's descriptive text (title, tags, notes, style notes, usage) is
     turned into a 384-number vector by the all-MiniLM-L6-v2 model, locally on CPU.
  2. Vectors are stored in library/vectors.db using the sqlite-vec extension.
  3. A query is embedded the same way; the nearest vectors (cosine distance)
     are the most similar entries.

This module is optional. Install it with `uv sync --extra semantic`. Without it
(or with DESIGNLIB_SEMANTIC=0) everything falls back to keyword search.

vectors.db is a cache like index.db: delete it and it is rebuilt on demand.
"""

import hashlib
import importlib.util
import os
import sqlite3
import sys
import threading
from contextlib import closing

from designlib import config
from designlib.core.schema import Entry

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DIMENSIONS = 384
MAX_DISTANCE = 0.75  # cosine distance; anything further away is "not related"

_model = None
_model_lock = threading.Lock()
_sync_lock = threading.Lock()  # warm-up and a first query may both try to sync


def _say(message: str) -> None:
    print(f"[designlib] {message}", file=sys.stderr)  # never stdout: it's the MCP channel


def installed() -> bool:
    # find_spec checks a package exists WITHOUT importing it. Importing
    # sentence_transformers pulls in PyTorch (~9 s), which must only happen in
    # the background warm-up, never while someone is waiting for a search.
    return all(importlib.util.find_spec(name) for name in ("sentence_transformers", "sqlite_vec"))


def enabled() -> bool:
    """On when the extra is installed, unless DESIGNLIB_SEMANTIC=0."""
    return os.environ.get("DESIGNLIB_SEMANTIC", "1") != "0" and installed()


def ready() -> bool:
    """True once the model is in memory, so a query won't have to wait for it."""
    return _model is not None


# ---------- the model ----------


def _load_model():
    global _model
    with _model_lock:
        if _model is None:
            # Keep the Hugging Face libraries quiet; their notices aren't useful here.
            os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
            os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
            os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
            from sentence_transformers import SentenceTransformer

            try:
                # Use the cached copy: works offline and skips a network check.
                _model = SentenceTransformer(MODEL_NAME, device="cpu", local_files_only=True)
            except OSError:
                _say(f"downloading {MODEL_NAME} once (about 90 MB, free, no account needed)...")
                _model = SentenceTransformer(MODEL_NAME, device="cpu")
    return _model


def encode(texts: list[str]) -> list[list[float]]:
    """Text -> unit-length vectors. Tests replace this with a fake to skip the model."""
    vectors = _load_model().encode(texts, normalize_embeddings=True, batch_size=64)
    return [vector.tolist() for vector in vectors]


def warm_up() -> None:
    """Load the model and embed new entries in a background thread (call on startup)."""

    def work():
        try:
            sync()
        except Exception as error:  # a failed warm-up must never crash the server
            _say(f"semantic search unavailable: {error}")

    if enabled():
        threading.Thread(target=work, name="semantic-warm-up", daemon=True).start()


# ---------- the vector store ----------


def entry_text(entry: Entry) -> str:
    """What we embed: the words that describe an entry. Code is left out on purpose:
    it would drown the description in class names."""
    notes = "\n".join(line for line in entry.notes.splitlines() if not line.startswith("Original file:"))
    parts = [
        entry.title,
        f"{entry.type.value} {entry.framework.value if entry.framework.value != 'none' else ''}",
        "Tags: " + ", ".join(entry.tags),
        notes,
        entry.style_notes.as_text(),
        f"Use when: {entry.when_to_use}" if entry.when_to_use else "",
        f"Avoid when: {entry.avoid_when}" if entry.avoid_when else "",
        entry.prompt or "",
    ]
    return "\n".join(part.strip() for part in parts if part and part.strip())


def text_hash(entry: Entry) -> str:
    """Fingerprint of entry_text(). Stored in the index so sync can spot changed text cheaply."""
    return hashlib.sha1(entry_text(entry).encode()).hexdigest()


VECTORS_VERSION = 2  # bump when the tables below change; old vectors.db files are rebuilt


def _connect() -> sqlite3.Connection:
    import sqlite_vec

    path = config.library_dir() / "vectors.db"
    conn = sqlite3.connect(path, timeout=10)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    if conn.execute("PRAGMA user_version").fetchone()[0] != VECTORS_VERSION:
        conn.executescript("DROP TABLE IF EXISTS embedded; DROP TABLE IF EXISTS entries_vec;")
        conn.execute(f"PRAGMA user_version = {VECTORS_VERSION}")
    conn.executescript(
        f"""
        CREATE TABLE IF NOT EXISTS embedded (
            id        TEXT PRIMARY KEY,
            text_hash TEXT NOT NULL    -- which version of the text this vector was made from
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS entries_vec USING vec0(
            id TEXT PRIMARY KEY,
            embedding float[{DIMENSIONS}] distance_metric=cosine
        );
        """
    )
    return conn


def sync() -> int:
    """Bring vectors.db up to date with the search index. Returns how many were embedded."""
    with _sync_lock:
        return _sync()


def _sync() -> int:
    import sqlite_vec

    from designlib.core.index import connect as connect_index

    with closing(connect_index()) as index, closing(_connect()) as vec:
        current = {row["id"]: row["text_hash"] for row in index.execute("SELECT id, text_hash FROM entries")}
        known = dict(vec.execute("SELECT id, text_hash FROM embedded").fetchall())

        # Entries that were deleted
        for entry_id in set(known) - set(current):
            vec.execute("DELETE FROM embedded WHERE id = ?", (entry_id,))
            vec.execute("DELETE FROM entries_vec WHERE id = ?", (entry_id,))

        # Entries that are new, or whose descriptive text changed.
        # (Toggling "favorite" doesn't change the text, so it costs nothing.)
        changed = [entry_id for entry_id, digest in current.items() if known.get(entry_id) != digest]
        if changed:
            texts = []
            for entry_id in changed:
                row = index.execute("SELECT data FROM entries WHERE id = ?", (entry_id,)).fetchone()
                texts.append(entry_text(Entry.model_validate_json(row["data"])))
            for entry_id, vector in zip(changed, encode(texts)):
                vec.execute("DELETE FROM entries_vec WHERE id = ?", (entry_id,))
                vec.execute(
                    "INSERT INTO entries_vec (id, embedding) VALUES (?, ?)",
                    (entry_id, sqlite_vec.serialize_float32(vector)),
                )
                vec.execute(
                    "INSERT OR REPLACE INTO embedded (id, text_hash) VALUES (?, ?)", (entry_id, current[entry_id])
                )
        vec.commit()
        return len(changed)


def nearest(query: str, k: int = 200) -> list[str]:
    """Ids of the entries closest in meaning to `query`, best first."""
    import sqlite_vec

    sync()
    [vector] = encode([query])
    with closing(_connect()) as vec:
        rows = vec.execute(
            "SELECT id, distance FROM entries_vec WHERE embedding MATCH ? AND k = ? ORDER BY distance",
            (sqlite_vec.serialize_float32(vector), k),
        ).fetchall()
    return [entry_id for entry_id, distance in rows if distance <= MAX_DISTANCE]
