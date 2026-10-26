"""Turn an entry's code into a standalone HTML document for <iframe srcdoc>.

The iframe is sandboxed with only `allow-scripts` (no `allow-same-origin`),
so snippet code runs in an opaque origin: it can't read the gallery's cookies,
DOM or storage. Tailwind entries load the locally vendored Tailwind v4 browser
build, which compiles the classes inside the iframe - no internet needed.

Some libraries need more than Tailwind to look right; SOURCE_EXTRAS adds their
(vendored, MIT-licensed) CSS/JS to the preview based on the entry's source.
"""

from functools import cache
from pathlib import Path

from designlib.core.schema import Entry, Framework

RENDERABLE = {Framework.html, Framework.tailwind}
VENDOR = Path(__file__).parent / "static" / "vendor"

TEMPLATE = """<!doctype html>
<html class="{html_class}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{head}
<style>
  html, body {{ margin: 0; min-height: 100vh; }}
  body:not(.phone) {{ display: grid; place-items: center; padding: 24px; box-sizing: border-box;
          font-family: system-ui, sans-serif; }}
  body.phone {{ height: 100vh; }}  /* phone screens fill the frame edge to edge */
</style>
</head>
<body class="{body_class}">
{code}
{tail}
</body>
</html>"""

TAILWIND = (
    # The browser build warns "not for production" once per preview, which floods the
    # console with dozens of identical lines. For a local gallery that's expected, so
    # hide just that one message.
    "<script>{const warn = console.warn; console.warn = (...args) => "
    "String(args[0]).includes('browser build of Tailwind') || warn(...args);}</script>"
    # Relative URL works: a srcdoc document inherits the gallery page's base URL.
    '<script src="/static/vendor/tailwind-browser.js"></script>'
)


@cache
def flowbite_theme() -> str:
    """Flowbite v3+ uses theme names like `bg-brand`. Tailwind's browser build only learns
    them from an inline <style type="text/tailwindcss">, so the theme is inlined."""
    return (VENDOR / "flowbite" / "theme.css").read_text(encoding="utf-8")


FRAMEWORK7_HEAD = (
    '<link rel="stylesheet" href="/static/vendor/framework7/framework7-bundle.min.css">'
    '<link rel="stylesheet" href="/static/vendor/framework7/icons.css">'
)
THEMES = ("ios", "md")  # Framework7 screens can be shown as iOS or Material (Android)


def source_extras(entry: Entry) -> tuple[str, str]:
    """(extra <head> HTML, extra end-of-<body> HTML) for libraries that need them."""
    if entry.source == "Framework7":
        return FRAMEWORK7_HEAD, ""
    if entry.source == "daisyUI":
        return '<link rel="stylesheet" href="/static/vendor/daisyui/daisyui.css">', ""
    if entry.source == "Flowbite":
        return (
            f'<style type="text/tailwindcss">{flowbite_theme()}</style>',
            '<script src="/static/vendor/flowbite/flowbite.min.js"></script>',  # dropdowns, modals...
        )
    return "", ""


def can_render(entry: Entry) -> bool:
    return bool(entry.code) and entry.framework in RENDERABLE


def build_srcdoc(entry: Entry, thumb: bool = False, theme: str = "ios") -> str | None:
    """thumb=True hides scrollbars, for the small card previews in the grid.
    theme picks iOS or Material styling for Framework7 screens."""
    if not can_render(entry):
        return None
    if entry.source == "Framework7":
        # Framework7 styles a screen from the theme class on <html> and expects its app root.
        code = (
            '<div id="app" class="framework7-root"><div class="view view-main view-init">'
            f"{entry.code}</div></div>"
        )
        head = ("<style>html { overflow: hidden; }</style>" if thumb else "") + FRAMEWORK7_HEAD
        theme = theme if theme in THEMES else "ios"
        return TEMPLATE.format(head=head, code=code, tail="", html_class=f"{theme} device-{theme}", body_class="phone")
    head = "<style>html { overflow: hidden; }</style>" if thumb else ""
    extra_head, tail = source_extras(entry)
    head += extra_head
    if entry.framework == Framework.tailwind:
        head += TAILWIND
    return TEMPLATE.format(head=head, code=entry.code, tail=tail, html_class="", body_class="")


def preview_kind(entry: Entry) -> str:
    """Which preview a card shows, in priority order."""
    if can_render(entry):
        return "code"
    if entry.local_image:
        return "local"
    if entry.preview_image_url:
        return "remote"
    return "none"
