"""Where things live on disk, and which address the gallery uses.

Every path is computed by a function (not a module-level constant) so tests can
point the whole app at a temporary folder by setting the DESIGNLIB_LIBRARY
environment variable.
"""

import os
from pathlib import Path

# src/designlib/config.py -> project root is three levels up
PROJECT_ROOT = Path(__file__).resolve().parents[2]

HOST = "127.0.0.1"  # local only: never expose the gallery to the network
PORT = int(os.environ.get("DESIGNLIB_PORT", "8000"))  # change only if 8000 is taken


def library_dir() -> Path:
    return Path(os.environ.get("DESIGNLIB_LIBRARY", PROJECT_ROOT / "library"))


def entries_dir() -> Path:
    return library_dir() / "entries"


def assets_dir() -> Path:
    """Your own screenshots. The only images we ever store locally."""
    return library_dir() / "assets" / "mine"


def styles_dir() -> Path:
    return library_dir() / "styles"


def index_path() -> Path:
    return library_dir() / "index.db"


def gallery_url(entry_id: str) -> str:
    return f"http://{HOST}:{PORT}/d/{entry_id}"
