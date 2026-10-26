"""Running the gallery: in the foreground (`designlib serve`) or in the background
of the MCP server, so the gallery_url links Claude hands out always open.

Only one process can own port 8000. Whoever starts first serves the gallery;
everyone else notices it's already up and leaves it alone.
"""

import socket
import sys
import threading
import time
import webbrowser

import httpx
import uvicorn

from designlib import config

RETRY_SECONDS = 30  # background mode: how often to check whether the gallery needs a new owner


def url(port: int = config.PORT) -> str:
    return f"http://{config.HOST}:{port}"


def port_in_use(port: int = config.PORT) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((config.HOST, port)) == 0


def gallery_is_running(port: int = config.PORT) -> bool:
    """True if *our* gallery answers on the port (not some other program)."""
    try:
        response = httpx.get(url(port) + "/", timeout=2)
    except httpx.HTTPError:
        return False
    return "Design Library" in response.text


def _uvicorn_server(port: int) -> uvicorn.Server:
    return uvicorn.Server(
        uvicorn.Config(
            "designlib.web.app:create_app",
            factory=True,
            host=config.HOST,  # 127.0.0.1 only: not reachable from other machines
            port=port,
            log_level="warning",
            access_log=False,
        )
    )


def serve_foreground(port: int = config.PORT, open_browser: bool = False, reload: bool = False) -> None:
    """`designlib serve`: run until Ctrl+C. If the gallery is already up, just open it."""
    if port_in_use(port):
        if gallery_is_running(port):
            print(f"The gallery is already running at {url(port)} (probably started by Claude).")
            if open_browser:
                webbrowser.open(url(port))
            return
        sys.exit(f"Port {port} is used by another program. Try: designlib serve --port {port + 1}")

    print(f"Design Library running at {url(port)}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(1.5, webbrowser.open, args=[url(port)]).start()  # give the server a moment
    if reload:
        uvicorn.run("designlib.web.app:create_app", factory=True, host=config.HOST, port=port, reload=True)
    else:
        _uvicorn_server(port).run()


def serve_in_background(port: int = config.PORT) -> threading.Thread:
    """Keep the gallery available while this process lives (used by the MCP server).

    Runs in a daemon thread, so it stops automatically when Claude closes the MCP server.
    If another process already serves the gallery, we wait and take over only if it goes away.
    """

    def keep_gallery_up():
        while True:
            if not port_in_use(port):
                try:
                    _uvicorn_server(port).run()  # blocks while we own the gallery
                except (OSError, SystemExit):
                    pass  # lost a race for the port to another process: fine, they serve it
            time.sleep(RETRY_SECONDS)

    thread = threading.Thread(target=keep_gallery_up, name="gallery", daemon=True)
    thread.start()
    return thread
