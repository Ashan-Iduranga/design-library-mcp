"""Read and write entries as JSON files in library/entries/.

These files are the source of truth: easy to read, diff and commit with git.
The SQLite index is only a fast copy that can always be rebuilt from them.
"""

import json
import sys
from collections.abc import Iterator
from pathlib import Path

from designlib import config
from designlib.core.schema import Entry, now


def entry_path(entry_id: str) -> Path:
    return config.entries_dir() / f"{entry_id}.json"


def save_entry(entry: Entry, touch: bool = True) -> Path:
    """Write one entry to <id>.json. `touch` bumps updated_at."""
    if touch:
        entry.updated_at = now()
    path = entry_path(entry.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = entry.model_dump(mode="json", exclude_none=False)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_entry(entry_id: str) -> Entry | None:
    path = entry_path(entry_id)
    if not path.exists():
        return None
    return Entry.model_validate_json(path.read_text(encoding="utf-8"))


def iter_entries() -> Iterator[Entry]:
    """Yield every valid entry. A broken file is reported, not fatal."""
    folder = config.entries_dir()
    if not folder.exists():
        return
    for path in sorted(folder.glob("*.json")):
        try:
            yield Entry.model_validate_json(path.read_text(encoding="utf-8"))
        except ValueError as error:
            # stderr, because stdout is the MCP protocol channel when running as a server
            print(f"[designlib] skipping invalid entry {path.name}: {error}", file=sys.stderr)


def delete_entry(entry_id: str) -> bool:
    path = entry_path(entry_id)
    if path.exists():
        path.unlink()
        return True
    return False
