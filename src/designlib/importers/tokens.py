"""Import design tokens and color scales:

  Open Props   (github.com/argyleink/open-props, MIT)  src/props.<group>.css
  Radix Colors (github.com/radix-ui/colors, MIT)       src/light.ts, src/dark.ts

Color entries get a small HTML swatch strip as their code, so the gallery shows the
actual colors and Claude gets copy-ready CSS custom properties.
"""

import re

from designlib.core.schema import Entry, slugify
from designlib.importers.common import files_under, open_repo, read_text, save_imported, title_case

# ---------- shared ----------


def swatches(title: str, rows: list[tuple[str, list[tuple[str, str]]]], css: str) -> str:
    """HTML: the copy-ready `css` (custom properties) plus one strip of labelled color
    chips per (row label, [(var name, value)]). Chips use the raw value, so light and
    dark rows can share variable names without overwriting each other."""
    html_rows = []
    for label, colors in rows:
        chips = "".join(
            f'<div style="background:{value}" title="{name}: {value}"><span>{name.split("-")[-1]}</span></div>'
            for name, value in colors
        )
        html_rows.append(f'<p>{label}</p><div class="row">{chips}</div>')
    return f"""<style>
{css}
.scale {{ font: 12px system-ui, sans-serif; width: min(720px, 100%); }}
.scale p {{ margin: 12px 0 4px; color: #555; }}
.scale .row {{ display: grid; grid-auto-flow: column; grid-auto-columns: 1fr; gap: 4px; }}
.scale .row div {{ height: 48px; border-radius: 6px; display: flex; align-items: end; padding: 4px; }}
.scale span {{ font-size: 10px; background: #fff9; border-radius: 3px; padding: 0 3px; }}
</style>
<div class="scale"><strong>{title}</strong>
{chr(10).join(html_rows)}
</div>"""


def css_block(selector: str, props: list[tuple[str, str]]) -> str:
    lines = "\n".join(f"  {name}: {value};" for name, value in props)
    return f"{selector} {{\n{lines}\n}}"


# ---------- Open Props ----------

OP_GITHUB = "https://github.com/argyleink/open-props/blob/main/src/"
OP_SKIP = re.compile(r"-hsl\.css$|\.src\.|^index|props\.(colors|colors-oklch.*|palette|gray-oklch)\.css$")
OP_COLORS = {"red", "pink", "purple", "violet", "indigo", "blue", "cyan", "teal", "green", "lime", "yellow",
             "orange", "choco", "brown", "sand", "camo", "jungle", "gray", "stone"}


def open_props_entries(archive, prefix: str) -> list[Entry]:
    entries = []
    for path in files_under(archive, prefix + "src/", r"^props\.[^/]+\.css$"):
        filename = path.rsplit("/", 1)[1]
        if OP_SKIP.search(filename):
            continue
        group = filename.removeprefix("props.").removesuffix(".css")
        css = read_text(archive, path).strip()
        props = re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", css)
        if not props:
            continue
        is_color = group in OP_COLORS
        code = swatches(f"Open Props {group}", [(group, props)], css) if is_color else css
        entries.append(Entry(
            id=f"open-props-{slugify(group)}",  # "masks.corner-cuts" -> "masks-corner-cuts"
            title=f"Open Props: {title_case(group)} {'color scale' if is_color else 'tokens'}",
            source="Open Props",
            url="https://open-props.style/#" + ("colors" if is_color else group.split(".")[0]),
            license="MIT",
            type="palette" if is_color else "token",
            tags=[group, "open-props", "css-variables", "tokens", *(["color"] if is_color else [])],
            framework="html" if is_color else "none",
            notes=f"{len(props)} CSS custom properties, e.g. {', '.join(n for n, _ in props[:4])}."
                  f"\n\nUse: npm i open-props, then @import \"open-props/{group}\" (or copy the variables)."
                  f"\n\nOriginal file: {OP_GITHUB}{filename}",
            code=code,
        ))
    return entries


# ---------- Radix Colors ----------

RADIX_GITHUB = "https://github.com/radix-ui/colors/blob/main/src/"
RADIX_STEPS = (
    "Steps 1-2: app and subtle backgrounds. 3-5: component backgrounds (normal, hover, pressed). "
    "6-8: borders and focus rings. 9-10: solid backgrounds (e.g. buttons). 11-12: low and high contrast text."
)


def parse_scales(ts: str) -> dict[str, list[tuple[str, str]]]:
    """'export const gray = { gray1: "#fcfcfc", ... }' -> {'gray': [('gray1', '#fcfcfc'), ...]}"""
    return {
        name: re.findall(r'(\w+):\s*"([^"]+)"', body)
        for name, body in re.findall(r"export const (\w+) = \{(.*?)\};", ts, re.DOTALL)
    }


def radix_entries(archive, prefix: str) -> list[Entry]:
    light = parse_scales(read_text(archive, prefix + "src/light.ts"))
    dark = parse_scales(read_text(archive, prefix + "src/dark.ts"))
    entries = []
    for name, steps in light.items():
        if name.endswith(("P3", "P3A", "A")) or f"{name}Dark" not in dark:
            continue  # keep the plain scale; alpha and P3 variants are listed in the notes
        dark_steps = dark[f"{name}Dark"]  # dark.ts calls it "grayDark", with steps "grayDark1"...
        to_vars = lambda scale: [(f"--{name}-{re.sub(r'^\D+', '', step)}", value) for step, value in scale]
        entries.append(Entry(
            id=f"radix-colors-{name}",
            title=f"Radix Colors: {title_case(name)} scale",
            source="Radix Colors",
            url="https://www.radix-ui.com/colors",
            license="MIT",
            type="palette",
            tags=[name, "radix", "color-scale", "color", "accessible", "dark-mode"],
            framework="html",
            notes=f"12-step {name} scale with a matching dark-mode scale. {RADIX_STEPS}"
                  f"\n\nAlso available: {name}A (alpha) and P3 wide-gamut versions."
                  f"\n\nUse: npm i @radix-ui/colors, then import \"@radix-ui/colors/{name}.css\" "
                  f"and \"@radix-ui/colors/{name}-dark.css\"."
                  f"\n\nOriginal file: {RADIX_GITHUB}light.ts",
            when_to_use="Building a UI color system with predictable steps for backgrounds, borders and text, "
                        "including dark mode.",
            code=swatches(
                f"Radix {name}",
                [("light", to_vars(steps)), ("dark", to_vars(dark_steps))],
                css_block(":root", to_vars(steps)) + "\n" + css_block(".dark", to_vars(dark_steps)),
            ),
        ))
    return entries


def run(limit: int = 0, refresh: bool = False) -> tuple[int, int]:
    with open_repo("argyleink", "open-props", refresh=refresh) as (archive, prefix):
        entries = open_props_entries(archive, prefix)
    with open_repo("radix-ui", "colors", refresh=refresh) as (archive, prefix):
        entries += radix_entries(archive, prefix)
    print(f"{len(entries)} token and color entries")
    return save_imported(entries[:limit] if limit > 0 else entries)
