"""MCP server (stdio) that lets Claude query your design library.

Run with `python -m designlib mcp`. Claude starts this process itself and talks
to it over stdin/stdout, so nothing here may print to stdout: logs go to stderr.

The official MCP Python SDK v2 renamed FastMCP to MCPServer; the decorator
style is the same: each @server.tool() function becomes a tool, its type hints
become the input schema and its docstring becomes the description Claude reads
to decide when to call it.
"""

import logging
import os
import sys
from typing import Any, Literal

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from designlib import config
from designlib.core import semantic, styleguide
from designlib.core.fetch import FetchError
from designlib.core.library import AlreadyInLibrary, add_from_url
from designlib.core.schema import Entry
from designlib.core.search import Filters, category_counts, get_entry, list_tags as tag_counts, search
from designlib.core.taxonomy import SLUGS, grouped

logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

EntryTypeName = Literal["style", "component", "screen", "interaction", "layout", "palette", "token"]
FrameworkName = Literal["html", "tailwind", "react", "react-native", "none"]
PlatformName = Literal["web", "mobile", "desktop", "any"]
# Every category slug from core/taxonomy.py, so Claude sees the full vocabulary in the schema.
CategoryName = Literal[tuple(SLUGS)]  # type: ignore[valid-type]

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)

server = MCPServer(
    name="design-library",
    title="Design Library",
    instructions=(
        "This is the user's own curated library of design references (styles, components, "
        "screens, layouts, palettes, tokens), each with notes on when to use it and when not to. "
        "Before designing or building any UI, call search_designs with the kind of thing you are "
        "building, then get_design on the best matches. Also call list_styles and "
        "get_style_guide, and follow the matching style guide's rules. Prefer these references "
        "and rules over generic defaults, and mention which references and style guide you "
        "used. Code marked license 'link-only' was not stored: "
        "use only the notes and link for those."
    ),
)


def summary(entry: Entry) -> dict[str, Any]:
    """A compact view for search results (no code, to keep responses small)."""
    return {
        "id": entry.id,
        "title": entry.title,
        "type": entry.type.value,
        "framework": entry.framework.value,
        "platform": entry.platform.value,
        "categories": entry.categories,
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
    platform: PlatformName | None = None,
    category: CategoryName | None = None,
    limit: int = 10,
    mode: Literal["hybrid", "keyword"] = "hybrid",
) -> list[dict[str, Any]]:
    """Search the user's curated design library. Call this FIRST whenever you are about to
    design or build a UI (a page, section, component, palette, interaction, etc.).

    query: free text, e.g. "pricing table", "dark dashboard", "toggle". Matches titles,
           tags, notes, style notes and code; partial words work.
    type: narrow to one kind of reference.
    tags: every tag listed must be present (use list_tags to see what exists).
    framework: narrow to html, tailwind, react or react-native code.
    platform: "web", "mobile" or "desktop" references ("any" = icons, colors, or unclear).
    category: what the reference is, e.g. "hero", "navigation", "pricing", "dashboard",
              "auth", "button" (call list_categories for all of them with counts).
    mode: "hybrid" (default) also finds entries similar in meaning, e.g. "calm" finds
          "quiet, minimal" (when semantic search is installed); "keyword" = exact words only.
    Results are ranked by relevance, without code. Use get_design(id) for full details.
    """
    filters = Filters(
        query=query, type=type, tags=tags, framework=framework, platform=platform,
        categories=[category] if category else None, mode=mode, limit=max(1, min(limit, 50)),
    )
    return [summary(entry) for entry in search(filters)]


@server.tool(annotations=READ_ONLY)
def get_design(id: str) -> dict[str, Any]:
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
def list_categories(platform: PlatformName | None = None) -> list[dict[str, Any]]:
    """List the library's categories (what references are: hero, navigation, pricing,
    dashboard, login & sign up, button, ...) grouped like a design gallery's sidebar, with
    how many references each has. Pass platform="web" / "mobile" / "desktop" to count only
    that platform. Use a category slug with search_designs(category=...)."""
    counts = category_counts(Filters(platform=platform))
    return [
        {
            "group": group,
            "categories": [
                {"slug": c.slug, "label": c.label, "count": counts.get(c.slug, 0)}
                for c in categories if counts.get(c.slug, 0)
            ],
        }
        for group, categories in grouped()
        if any(counts.get(c.slug, 0) for c in categories)
    ]


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
def add_design(url: str, type: EntryTypeName, tags: list[str] | None = None, notes: str = "") -> dict[str, Any]:
    """Save a web page to the library as a link-only reference, when the user asks you to
    remember or bookmark a design. Only metadata is fetched (title, description, preview image
    link), respecting robots.txt. No code or images are copied.

    type: what the page is an example of. notes: why the user likes it / how to use it.
    """
    warning = None
    try:
        try:
            entry = add_from_url(url, type=type, tags=tags, notes=notes)
        except FetchError as error:
            # Still save the link; we just couldn't (or weren't allowed to) read the page.
            warning = f"Saved without page details: {error}"
            entry = add_from_url(url, type=type, tags=tags, notes=notes, fetch=False)
    except AlreadyInLibrary as already:
        entry, warning = already.entry, "Already in your library; nothing was added."
    result = summary(entry)
    if warning:
        result["warning"] = warning
    return result


def main() -> None:
    semantic.warm_up()  # load the meaning model while Claude is still starting up
    if os.environ.get("DESIGNLIB_GALLERY_WITH_MCP", "1") != "0":
        # Serve the gallery too, so every gallery_url we return actually opens.
        from designlib.web.server import serve_in_background

        serve_in_background()
    server.run("stdio")
