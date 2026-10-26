"""MCP tests: the tool functions directly, the registered tool list, and one real
stdio round trip (start the server as a subprocess and talk MCP to it)."""

import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from designlib import mcp_server
from designlib.core import library
from designlib.core.fetch import FetchError, PageMeta

EXPECTED_TOOLS = {"search_designs", "get_design", "list_categories", "list_tags", "list_styles", "get_style_guide", "add_design"}


def test_tools_are_registered_with_descriptions():
    tools = asyncio.run(mcp_server.server.list_tools())
    assert {tool.name for tool in tools} == EXPECTED_TOOLS
    for tool in tools:
        assert len(tool.description or "") > 40, f"{tool.name} needs a real description"
        # Structured output (an output schema) lets Claude read results as data, not text.
        assert tool.output_schema, f"{tool.name} has no output schema"
    search = next(t for t in tools if t.name == "search_designs")
    assert "component" in str(search.input_schema)  # the type enum is visible to Claude


def test_search_designs(sample_entries):
    results = mcp_server.search_designs("pricing")
    assert results[0]["id"] == "pricing-table-aaaaaa"
    assert results[0]["gallery_url"] == "http://127.0.0.1:8000/d/pricing-table-aaaaaa"
    assert "code" not in results[0] and results[0]["has_code"] is True
    assert [r["id"] for r in mcp_server.search_designs(type="screen")] == ["calm-dashboard-bbbbbb"]
    assert mcp_server.search_designs(tags=["button"], framework="html")[0]["title"] == "Glass buttons"


def test_get_design_includes_code_and_gallery_url(sample_entries):
    design = mcp_server.get_design("pricing-table-aaaaaa")
    assert design["code"].startswith("<div")
    assert design["gallery_url"].endswith("/d/pricing-table-aaaaaa")
    assert "error" in mcp_server.get_design("nope")


def test_list_tags(sample_entries):
    assert {"tag": "pricing", "count": 1} in mcp_server.list_tags()


def test_style_guides(temp_library):
    (temp_library / "styles" / "quiet-product.md").write_text(
        "# Quiet product\n\nCalm and dense.\n\n## Palette\n- ink", encoding="utf-8"
    )
    assert mcp_server.list_styles() == [{"name": "quiet-product", "summary": "Calm and dense."}]
    assert "## Palette" in mcp_server.get_style_guide("Quiet Product")
    assert "Available: quiet-product" in mcp_server.get_style_guide("loud")


def test_add_design_falls_back_when_fetch_fails(monkeypatch):
    def refuse(url):
        raise FetchError("robots.txt does not allow fetching this page")

    monkeypatch.setattr(library, "fetch_metadata", refuse)
    result = mcp_server.add_design("https://godly.website/x", type="style", tags=["bold"], notes="loud type")
    assert "robots.txt" in result["warning"]
    assert result["license"] == "link-only" and result["tags"] == ["bold"]

    monkeypatch.setattr(library, "fetch_metadata", lambda url: PageMeta(url=url, title="Nice", source="Godly"))
    assert "warning" not in mcp_server.add_design("https://godly.website/y", type="style")


def test_stdio_round_trip(sample_entries, temp_library):
    """Start `python -m designlib mcp` exactly as Claude would and call a tool."""

    async def run():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "designlib", "mcp"],
            env={**os.environ, "DESIGNLIB_LIBRARY": str(temp_library)},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                result = await session.call_tool("search_designs", {"query": "glass"})
                return {t.name for t in tools.tools}, result

    names, result = asyncio.run(run())
    assert names == EXPECTED_TOOLS
    assert not result.is_error
    assert "glass-buttons-cccccc" in str(result.content)
