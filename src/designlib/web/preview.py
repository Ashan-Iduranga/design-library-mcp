"""Turn an entry's code into a standalone HTML document for <iframe srcdoc>.

The iframe is sandboxed with only `allow-scripts` (no `allow-same-origin`),
so snippet code runs in an opaque origin: it can't read the gallery's cookies,
DOM or storage. Tailwind entries load the locally vendored Tailwind v4 browser
build, which compiles the classes inside the iframe - no internet needed.
"""

from designlib.core.schema import Entry, Framework

RENDERABLE = {Framework.html, Framework.tailwind}

TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{head}
<style>
  html, body {{ margin: 0; min-height: 100vh; }}
  body {{ display: grid; place-items: center; padding: 24px; box-sizing: border-box;
          font-family: system-ui, sans-serif; }}
</style>
</head>
<body>
{code}
</body>
</html>"""


def can_render(entry: Entry) -> bool:
    return bool(entry.code) and entry.framework in RENDERABLE


def build_srcdoc(entry: Entry) -> str | None:
    if not can_render(entry):
        return None
    head = ""
    if entry.framework == Framework.tailwind:
        # Relative URL works: a srcdoc document inherits the gallery page's base URL.
        head = '<script src="/static/vendor/tailwind-browser.js"></script>'
    return TEMPLATE.format(head=head, code=entry.code)


def preview_kind(entry: Entry) -> str:
    """Which preview a card shows, in priority order."""
    if can_render(entry):
        return "code"
    if entry.local_image:
        return "local"
    if entry.preview_image_url:
        return "remote"
    return "none"
