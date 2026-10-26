"""Import shadcn/ui (github.com/shadcn-ui/ui, MIT): UI components, blocks, charts, examples.

Repo layout we rely on (the "new-york-v4" style, the current default):
  apps/v4/registry/new-york-v4/<kind>/_registry.ts   list of items: name, description, files
  apps/v4/registry/new-york-v4/<path from files>     the source code of each item

The code is React + Tailwind, so the gallery shows it as code (no live preview).
Each entry includes the exact `npx shadcn@latest add ...` command, so Claude Code can
install the real component into a project instead of copying text.
"""

import re

from designlib.core.schema import Entry
from designlib.importers.common import open_repo, read_text, round_robin, save_imported, title_case

REGISTRY = "apps/v4/registry/new-york-v4/"
GITHUB = "https://github.com/shadcn-ui/ui/blob/main/" + REGISTRY

# registry folder -> (entry type, tag, link to the docs for this kind)
KINDS = {
    "ui": ("component", "ui", "https://ui.shadcn.com/docs/components/{name}"),
    "blocks": ("layout", "block", "https://ui.shadcn.com/blocks#{name}"),
    "charts": ("component", "chart", "https://ui.shadcn.com/charts"),
    "examples": ("component", "example", None),
}

# One top-level item: "  {" ... "  }," (two-space indent). Fields can come in any order.
ITEM = re.compile(r'\n  \{\s*name:\s*"(?P<name>[^"]+)",(?P<body>.*?)\n  \},', re.DOTALL)


def parse_registry(text: str) -> list[dict]:
    """Read the items out of a _registry.ts file without running TypeScript."""
    items = []
    for match in ITEM.finditer(text):
        body = match.group("body")
        description = re.search(r'description:\s*"((?:[^"\\]|\\.)*)"', body)
        categories = re.search(r"categories:\s*\[([^\]]*)\]", body)
        items.append({
            "name": match.group("name"),
            "description": description.group(1) if description else "",
            "files": re.findall(r'path:\s*"([^"]+)"', body),
            "categories": re.findall(r'"([^"]+)"', categories.group(1)) if categories else [],
        })
    return items


DOCS = "apps/v4/content/docs/components/{base}/{name}.mdx"


def docs_description(archive, prefix: str, name: str) -> str:
    """UI components have no description in the registry, but their docs page does.
    Examples like "button-destructive" use their component's page ("button")."""
    parts = name.split("-")
    for length in range(len(parts), 0, -1):  # "button-destructive", then "button"
        candidate = "-".join(parts[:length])
        for base in ("radix", "base", "aria"):  # new-york-v4 is built on Radix, so prefer its docs
            path = prefix + DOCS.format(base=base, name=candidate)
            if path in archive.namelist():
                found = re.search(r"^description:\s*(.+)$", read_text(archive, path), re.MULTILINE)
                if found:
                    return found.group(1).strip().strip('"')
    return ""


def build_entry(archive, prefix: str, kind: str, item: dict) -> Entry | None:
    entry_type, tag, docs = KINDS[kind]
    sources = []
    for path in item["files"]:
        full = prefix + REGISTRY + path
        if full in archive.namelist():
            sources.append((path, read_text(archive, full)))
    if not sources:
        return None
    if len(sources) == 1:
        code = sources[0][1]
    else:  # blocks are often several files: keep them together, labelled
        code = "\n\n".join(f"// File: {path}\n{text}" for path, text in sources)

    name = item["name"]
    installable = kind in ("ui", "blocks")
    description = item["description"] or docs_description(archive, prefix, name)
    notes = description or f"shadcn/ui {tag}: {title_case(name)}."
    if installable:
        notes += f"\n\nInstall into a project: npx shadcn@latest add {name}"
    notes += f"\n\nOriginal file: {GITHUB}{sources[0][0]}"
    name_words = [w for w in name.split("-") if not w.isdigit()]
    return Entry(
        id=f"shadcn-{kind}-{name}",
        title=f"{title_case(name)} ({'shadcn/ui ' + tag if tag != 'ui' else 'shadcn/ui'})",
        source="shadcn/ui",
        url=docs.format(name=name) if docs else GITHUB + sources[0][0],
        license="MIT",
        type=entry_type,
        tags=[tag, *name_words, *item["categories"], "shadcn", "react", "tailwind"],
        framework="react",
        notes=notes,
        code=code,
        prompt=f"npx shadcn@latest add {name}" if installable else None,
    )


def run(limit: int = 0, refresh: bool = False) -> tuple[int, int]:
    groups: dict[str, list[Entry]] = {}
    with open_repo("shadcn-ui", "ui", refresh=refresh) as (archive, prefix):
        for kind in KINDS:
            registry_file = f"{prefix}{REGISTRY}{kind}/_registry.ts"
            for item in parse_registry(read_text(archive, registry_file)):
                entry = build_entry(archive, prefix, kind, item)
                if entry:
                    groups.setdefault(kind, []).append(entry)
    print({kind: len(entries) for kind, entries in groups.items()})
    return save_imported(round_robin(groups, limit))
