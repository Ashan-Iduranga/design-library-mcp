"""Import Magic UI (github.com/magicuidesign/magicui, MIT): animated React components.

Repo layout we rely on:
  apps/www/registry.json        every item: name, type, title, description, files
  apps/www/<files[].path>       the source code

Like shadcn/ui, it's React + Tailwind (code only, no live preview) and installs with
the shadcn CLI, so each entry carries the install command.
"""

import json

from designlib.core.schema import Entry
from designlib.importers.common import open_repo, read_text, round_robin, save_imported, title_case

APP = "apps/www/"
GITHUB = "https://github.com/magicuidesign/magicui/blob/main/" + APP
KINDS = {"registry:ui": "component", "registry:example": "example"}


def build_entry(archive, prefix: str, item: dict) -> Entry | None:
    kind = KINDS.get(item.get("type", ""))
    paths = [f["path"] for f in item.get("files", []) if prefix + APP + f["path"] in archive.namelist()]
    if kind is None or not paths:
        return None
    code = "\n\n".join(
        (f"// File: {p}\n" if len(paths) > 1 else "") + read_text(archive, prefix + APP + p) for p in paths
    )
    name = item["name"]
    title = item.get("title") or title_case(name)
    notes = item.get("description") or f"Magic UI {kind}: {title}."
    install = f"npx shadcn@latest add @magicui/{name}"
    if kind == "component":
        notes += f"\n\nInstall into a project: {install}"
    deps = item.get("dependencies") or []
    if deps:
        notes += f"\n\nnpm dependencies: {', '.join(deps)}"
    notes += f"\n\nOriginal file: {GITHUB}{paths[0]}"
    base = name.removesuffix("-demo").split("-demo-")[0]
    return Entry(
        id=f"magicui-{name}",
        title=f"{title} (Magic UI{' example' if kind == 'example' else ''})",
        source="Magic UI",
        url=f"https://magicui.design/docs/components/{base}",
        license="MIT",
        type="interaction",  # Magic UI is all about motion and effects
        tags=[*name.split("-"), "animation", "magicui", "react", "tailwind", *(["example"] if kind == "example" else [])],
        framework="react",
        notes=notes,
        code=code,
        prompt=install if kind == "component" else None,
    )


def run(limit: int = 0, refresh: bool = False) -> tuple[int, int]:
    groups: dict[str, list[Entry]] = {}
    with open_repo("magicuidesign", "magicui", refresh=refresh) as (archive, prefix):
        items = json.loads(read_text(archive, prefix + APP + "registry.json"))["items"]
        for item in items:
            entry = build_entry(archive, prefix, item)
            if entry:
                groups.setdefault(item["type"], []).append(entry)
    print({kind: len(entries) for kind, entries in groups.items()})
    return save_imported(round_robin(groups, limit))
