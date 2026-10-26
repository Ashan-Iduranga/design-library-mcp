"""MCP server (stdio) that lets Claude query your design library.

Run with `python -m designlib mcp`. Claude starts this process itself and talks
to it over stdin/stdout, so nothing here may print to stdout: logs go to stderr.

The official MCP Python SDK v2 renamed FastMCP to MCPServer; the decorator
style is the same: each @server.tool() function becomes a tool, its type hints
become the input schema and its docstring becomes the description Claude reads
to decide when to call it.
"""

import logging
import sys
from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from designlib import config
from designlib.core import styleguide
from designlib.core.fetch import FetchError
from designlib.core.library import add_from_url
from designlib.core.schema import Entry
from designlib.core.search import Filters, get_entry, list_tags as tag_counts, search

logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

EntryTypeName = Literal["style", "component", "screen", "interaction", "layout", "palette", "token"]
FrameworkName = Literal["html", "tailwind", "react", "none"]

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)

server = MCPServer(
    name="design-library",
    title="Design Library",
    instructions=(
        "This is the user's own curated library of design references (styles, components, "
        "screens, layouts, palettes, tokens), each with notes on when to use it and when not to. "
        "Before designing or building any UI, call search_designs with the kind of thing you are "
        "building, then get_design on the best matches, and check list_styles/get_style_guide "
        "for the user's saved style rules. Prefer these references over generic defaults, and "
        "mention which references you used. Code marked license 'link-only' was not stored: "
        "use only the notes and link for those."
    ),
)


def summary(entry: Entry) -> dict:
    """A compact view for search results (no code, to keep responses small)."""
    return {
        "id": entry.id,
        "title": entry.title,
        "type": entry.type.value,
        "framework": entry.framework.value,
        "source": entry.source,
        "license": entry.license,
        "tags": entry.tags,
        "rating": entry.my_rating,
        "favorite": entry.favorite,
        "has_code": entry.code is not None,
        "when_to_use": entry.when_to_use,
        "avoid_when": entry.avoid_when,
        "gallery_url": config.gallery_url(entry.id),
    }


@server.tool(annotations=READ_ONLY)
def search_designs(
    query: str = "",
    type: EntryTypeName | None = None,
    tags: list[str] | None = None,
    framework: FrameworkName | None = None,
    limit: int = 10,
) -> list[dict]:
    """Search the user's curated design library. Call this FIRST whenever you are about to
    design or build a UI (a page, section, component, palette, interaction, etc.).

    query: free text, e.g. "pricing table", "dark dashboard", "toggle". Matches titles,
           tags, notes, style notes and code; partial words work.
    type: narrow to one kind of reference.
    tags: every tag listed must be present (use list_tags to see what exists).
    framework: narrow to html, tailwind or react code.
    Results are ranked by relevance, without code. Use get_design(id) for full details.
    """
    filters = Filters(query=query, type=type, tags=tags, framework=framework, limit=max(1, min(limit, 50)))
    return [summary(entry) for entry in search(filters)]


@server.tool(annotations=READ_ONLY)
def get_design(id: str) -> dict:
    """Get one reference in full: code (when its license allows storing it), prompt,
    style notes (palette, fonts, spacing, mood), when to use / avoid, source URL, license,
    and gallery_url, a local page where the user can see a live preview.
    Use the ids returned by search_designs. Respect the license field when reusing code.
    """
    entry = get_entry(id)
    if entry is None:
        return {"error": f"No design with id {id!r}. Use search_designs to find ids."}
    data = entry.model_dump(mode="json")
    data["gallery_url"] = config.gallery_url(entry.id)
    return data


@server.tool(annotations=READ_ONLY)
def list_tags(limit: int = 100) -> list[dict]:
    """List the tags used in the library with how many entries have each, most used first.
    Use it to discover vocabulary before filtering search_designs by tags."""
    return [{"tag": tag, "count": count} for tag, count in tag_counts()[: max(1, limit)]]


@server.tool(annotations=READ_ONLY)
def list_styles() -> list[dict]:
    """List the user's saved style guides (name + one-line summary).
    Check this at the start of UI work; if one fits, read it with get_style_guide."""
    return styleguide.list_styles()


@server.tool(annotations=READ_ONLY)
def get_style_guide(style: str) -> str:
    """Get a saved style guide by name (from list_styles): the user's own rules for palette,
    typography, spacing, and do/don't. Follow these rules when they apply to the task."""
    text = styleguide.get_style_guide(style)
    if text is None:
        names = ", ".join(s["name"] for s in styleguide.list_styles()) or "none yet"
        return f"No style guide named {style!r}. Available: {names}."
    return text


@server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=True))
def add_design(url: str, type: EntryTypeName, tags: list[str] | None = None, notes: str = "") -> dict:
    """Save a web page to the library as a link-only reference, when the user asks you to
    remember or bookmark a design. Only metadata is fetched (title, description, preview image
    link), respecting robots.txt. No code or images are copied.

    type: what the page is an example of. notes: why the user likes it / how to use it.
    """
    warning = None
    try:
        entry = add_from_url(url, type=type, tags=tags, notes=notes)
    except FetchError as error:
        # Still save the link; we just couldn't (or weren't allowed to) read the page.
        warning = f"Saved without page details: {error}"
        entry = add_from_url(url, type=type, tags=tags, notes=notes, fetch=False)
    result = summary(entry)
    if warning:
        result["warning"] = warning
    return result


def main() -> None:
    server.run("stdio")
