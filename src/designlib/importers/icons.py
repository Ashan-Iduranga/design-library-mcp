"""Import icon sets as browsable, searchable groups:

  Lucide    (github.com/lucide-icons/lucide, ISC)  one entry per category (42)
  Heroicons (github.com/tailwindlabs/heroicons, MIT) one entry per style (4)

One entry per *group* rather than per icon: thousands of single-icon entries would
crowd icons into every unrelated search. Each entry's code is a grid of the real SVGs
(so the gallery shows them), and its notes list every icon name, so searching
"calendar icon" still finds the right group. Claude then uses the npm package.
"""

import json
import re

from designlib.core.schema import Entry
from designlib.importers.common import files_under, open_repo, read_text, save_imported, title_case

GRID_STYLE = """<style>
.icons { display: grid; grid-template-columns: repeat(auto-fill, minmax(84px, 1fr)); gap: 8px;
         width: min(960px, 100%); font: 10px system-ui, sans-serif; color: #222; }
.icons figure { margin: 0; display: grid; justify-items: center; gap: 6px; padding: 10px 4px;
                border: 1px solid #eee; border-radius: 8px; text-align: center; word-break: break-word; }
.icons svg { width: 24px; height: 24px; }
</style>"""


def compact_svg(svg: str) -> str:
    return re.sub(r"\s+", " ", svg).replace("> <", "><").strip()


def icon_grid(icons: list[tuple[str, str]]) -> str:
    """HTML grid of (name, svg) pairs."""
    cells = "".join(f"<figure>{compact_svg(svg)}<figcaption>{name}</figcaption></figure>" for name, svg in icons)
    return f'{GRID_STYLE}\n<div class="icons">{cells}</div>'


# ---------- Lucide ----------

LUCIDE_REACT = "lucide-react"


def pascal(name: str) -> str:
    """'arrow-down-left' -> 'ArrowDownLeft' (the React component name)."""
    return "".join(part.capitalize() for part in name.split("-"))


def lucide_entries(archive, prefix: str) -> list[Entry]:
    categories = {}
    for path in files_under(archive, prefix + "categories/", r"^[^/]+\.json$"):
        info = json.loads(read_text(archive, path))
        categories[path.rsplit("/", 1)[1].removesuffix(".json")] = info

    members: dict[str, list[tuple[str, str, list[str]]]] = {name: [] for name in categories}
    for path in files_under(archive, prefix + "icons/", r"^[^/]+\.json$"):
        name = path.rsplit("/", 1)[1].removesuffix(".json")
        svg_path = path.removesuffix(".json") + ".svg"
        if svg_path not in archive.namelist():
            continue
        info = json.loads(read_text(archive, path))
        for category in info.get("categories", []):
            if category in members:
                members[category].append((name, read_text(archive, svg_path), info.get("tags", [])))

    entries = []
    for category, icons in members.items():
        if not icons:
            continue
        info = categories[category]
        names = [name for name, _, _ in icons]
        keywords = sorted({tag for _, _, tags in icons for tag in tags})
        example = names[0]
        entries.append(Entry(
            id=f"lucide-{category}",
            title=f"Lucide icons: {info.get('title', title_case(category))} ({len(icons)})",
            source="Lucide",
            url=f"https://lucide.dev/icons/categories#{category}",
            license="ISC",
            type="component",
            tags=["icons", "icon", category, "lucide", "svg"],
            framework="html",
            notes=f"{info.get('description', '')}\n\n"
                  f"Icons: {', '.join(names)}.\n\n"
                  f"Keywords: {', '.join(keywords[:200])}.\n\n"
                  f"Use in React: npm i {LUCIDE_REACT}, then "
                  f"import {{ {pascal(example)} }} from \"{LUCIDE_REACT}\"; <{pascal(example)} size={{20}} />. "
                  f"Other frameworks: lucide (vanilla), lucide-vue-next, lucide-svelte. Or copy the SVG.",
            code=icon_grid([(name, svg) for name, svg, _ in icons]),
        ))
    return entries


# ---------- Heroicons ----------

HEROICON_STYLES = {
    # folder: (title, React import path, size note)
    "24/outline": ("Outline (24px)", "@heroicons/react/24/outline", "1.5px stroke, for primary navigation and marketing"),
    "24/solid": ("Solid (24px)", "@heroicons/react/24/solid", "filled, for primary navigation and marketing"),
    "20/solid": ("Mini (20px)", "@heroicons/react/20/solid", "filled, for smaller elements like buttons and form fields"),
    "16/solid": ("Micro (16px)", "@heroicons/react/16/solid", "filled, for tight, high-density UIs"),
}


def heroicons_entries(archive, prefix: str) -> list[Entry]:
    entries = []
    for folder, (title, import_path, use) in HEROICON_STYLES.items():
        paths = files_under(archive, f"{prefix}optimized/{folder}/", r"^[^/]+\.svg$")
        icons = [(p.rsplit("/", 1)[1].removesuffix(".svg"), read_text(archive, p)) for p in paths]
        if not icons:
            continue
        example = pascal(icons[0][0]) + "Icon"
        entries.append(Entry(
            id=f"heroicons-{folder.replace('/', '-')}",
            title=f"Heroicons: {title} ({len(icons)} icons)",
            source="Heroicons",
            url="https://heroicons.com/" + folder.split("/")[1],
            license="MIT",
            type="component",
            tags=["icons", "icon", "heroicons", "svg", "tailwind", folder.split("/")[1]],
            framework="html",
            notes=f"Heroicons {title}: {use}. Made by the Tailwind CSS team.\n\n"
                  f"Icons: {', '.join(name for name, _ in icons)}.\n\n"
                  f"Use in React: npm i @heroicons/react, then "
                  f"import {{ {example} }} from \"{import_path}\"; <{example} className=\"size-6\" />. "
                  f"Or copy the SVG.",
            code=icon_grid(icons),
        ))
    return entries


def run(limit: int = 0, refresh: bool = False) -> tuple[int, int]:
    with open_repo("lucide-icons", "lucide", license="ISC", refresh=refresh) as (archive, prefix):
        entries = lucide_entries(archive, prefix)
    with open_repo("tailwindlabs", "heroicons", branch="master", refresh=refresh) as (archive, prefix):
        entries += heroicons_entries(archive, prefix)
    print(f"{len(entries)} icon groups")
    return save_imported(entries[:limit] if limit > 0 else entries)
