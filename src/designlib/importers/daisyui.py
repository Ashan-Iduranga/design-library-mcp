"""Import daisyUI's component examples (github.com/saadeghi/daisyui, MIT).

Repo layout we rely on:
  packages/docs/src/routes/(routes)/components/<name>/+page.md
    front matter "title:" / "desc:"
    "### ~Example title" followed by a ```html code block

In the docs, class names are written with a "$$" marker (e.g. "$$btn") so the site
can add a prefix; we remove it to get normal daisyUI classes.
Previews load daisyUI's CSS (vendored, MIT), see web/preview.py.
"""

import re

from designlib.core.schema import Entry, slugify
from designlib.importers.common import files_under, open_repo, read_text, round_robin, save_imported, title_case

DOCS = "packages/docs/src/routes/(routes)/components/"
GITHUB = "https://github.com/saadeghi/daisyui/blob/master/" + DOCS
EXAMPLE = re.compile(r"^###\s+~?(?P<title>.+?)\s*$(?P<between>.*?)^```html\s*$(?P<code>.*?)^```", re.MULTILINE | re.DOTALL)


def front_matter(text: str, key: str) -> str:
    found = re.search(rf"^{key}:\s*(.+)$", text, re.MULTILINE)
    return found.group(1).strip().strip("\"'") if found else ""


def page_entries(name: str, text: str) -> list[Entry]:
    page_title = front_matter(text, "title") or title_case(name)
    description = front_matter(text, "desc")
    entries = []
    seen = set()
    for match in EXAMPLE.finditer(text):
        title = match.group("title").strip()
        if "###" in match.group("between"):
            continue  # the html block belongs to a later heading; that one will match it
        code = match.group("code").strip().replace("$$", "")
        entry_id = f"daisyui-{name}-{slugify(title)[:40].rstrip('-')}"
        if not code or entry_id in seen:
            continue
        seen.add(entry_id)
        entries.append(Entry(
            id=entry_id,
            title=f"{page_title}: {title} (daisyUI)",
            source="daisyUI",
            url=f"https://daisyui.com/components/{name}/",
            license="MIT",
            type="component",
            tags=[name, "daisyui", "tailwind"],
            framework="tailwind",
            notes=f"{description}\n\nNeeds daisyUI installed (npm i -D daisyui, then @plugin \"daisyui\" in your CSS)."
                  f"\n\nOriginal file: {GITHUB}{name}/+page.md",
            code=code,
        ))
    return entries


def run(limit: int = 0, refresh: bool = False) -> tuple[int, int]:
    groups: dict[str, list[Entry]] = {}
    with open_repo("saadeghi", "daisyui", branch="master", refresh=refresh) as (archive, prefix):
        for path in files_under(archive, prefix + DOCS, r"^[^/]+/\+page\.md$"):
            name = path.removeprefix(prefix + DOCS).split("/")[0]
            found = page_entries(name, read_text(archive, path))
            if found:
                groups[name] = found
    print(f"{sum(len(v) for v in groups.values())} examples from {len(groups)} components")
    return save_imported(round_robin(groups, limit))
