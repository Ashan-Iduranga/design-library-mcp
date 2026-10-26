"""The gallery runner: foreground `serve`, and the background gallery inside the MCP server."""

import asyncio
import os
import socket
import sys
import time

import httpx
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from designlib.web import server


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_until_up(port: int, seconds: float = 20) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if server.gallery_is_running(port):
            return True
        time.sleep(0.2)
    return False


def test_serve_when_gallery_already_running_just_opens_it(monkeypatch, capsys):
    opened = []
    monkeypatch.setattr(server, "port_in_use", lambda port: True)
    monkeypatch.setattr(server, "gallery_is_running", lambda port: True)
    monkeypatch.setattr(server.webbrowser, "open", opened.append)
    server.serve_foreground(port=8123, open_browser=True)  # must not crash with "address in use"
    assert "already running" in capsys.readouterr().out
    assert opened == ["http://127.0.0.1:8123"]


def test_serve_when_port_taken_by_another_program(monkeypatch):
    monkeypatch.setattr(server, "port_in_use", lambda port: True)
    monkeypatch.setattr(server, "gallery_is_running", lambda port: False)
    with pytest.raises(SystemExit, match="used by another program"):
        server.serve_foreground(port=8123)


def test_background_gallery_serves_pages(sample_entries):
    port = free_port()
    server.serve_in_background(port)
    assert wait_until_up(port)
    assert httpx.get(f"http://127.0.0.1:{port}/d/glass-buttons-cccccc").status_code == 200
    # A second background runner on the same port must not crash; it just waits.
    server.serve_in_background(port)
    assert server.gallery_is_running(port)


def test_mcp_server_makes_gallery_urls_work(sample_entries, temp_library):
    """Start the MCP server like Claude does; the gallery_url it returns must open."""
    port = free_port()

    async def run():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "designlib", "mcp"],
            env={
                **os.environ,
                "DESIGNLIB_LIBRARY": str(temp_library),
                "DESIGNLIB_GALLERY_WITH_MCP": "1",
                "DESIGNLIB_PORT": str(port),
            },
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("get_design", {"id": "glass-buttons-cccccc"})
                gallery_url = result.structured_content["gallery_url"]
                assert gallery_url == f"http://127.0.0.1:{port}/d/glass-buttons-cccccc"
                assert await asyncio.to_thread(wait_until_up, port)
                response = await asyncio.to_thread(httpx.get, gallery_url)
                return response.status_code, response.text

    status, page = asyncio.run(run())
    assert status == 200 and "Glass buttons" in page
