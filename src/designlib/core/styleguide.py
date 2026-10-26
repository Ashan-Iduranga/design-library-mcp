"""Your saved style guides: one Markdown file per style in library/styles/.

A style guide is your own rules for a look (palette, type, spacing, do/don't),
so Claude can follow them instead of guessing.
"""

from designlib import config
from designlib.core.schema import slugify


def _files() -> dict[str, str]:
    """style name (file stem) -> file path"""
    folder = config.styles_dir()
    if not folder.exists():
        return {}
    return {path.stem: str(path) for path in sorted(folder.glob("*.md"))}


def _summary(text: str) -> str:
    """The first paragraph after the heading, as a one-line description."""
    for block in text.split("\n\n"):
        block = block.strip()
        if block and not block.startswith("#"):
            return " ".join(block.split())
    return ""


def list_styles() -> list[dict]:
    styles = []
    for name, path in _files().items():
        with open(path, encoding="utf-8") as file:
            styles.append({"name": name, "summary": _summary(file.read())})
    return styles


def get_style_guide(style: str) -> str | None:
    """Find a guide by name. 'Quiet Product', 'quiet-product' and 'quiet_product' all match."""
    files = _files()
    wanted = slugify(style)
    for name, path in files.items():
        if slugify(name) == wanted:
            with open(path, encoding="utf-8") as file:
                return file.read()
    return None
