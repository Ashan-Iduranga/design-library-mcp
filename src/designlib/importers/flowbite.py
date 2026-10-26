"""Import Flowbite's open-source examples (github.com/themesberg/flowbite, MIT).

Repo layout we rely on:
  content/<group>/<page>.md     docs pages (components, forms, typography)
    front matter "title:" / "description:"
    "## Section heading" followed by
    {{< example ... >}} <html snippet> {{< /example >}}

Only the open-source library is used. Flowbite Pro / Blocks are paid and never touched.
Previews load Flowbite's theme and JS (vendored, MIT), see web/preview.py.
"""

import re

from designlib.core.schema import Entry, slugify
from designlib.importers.common import files_under, open_repo, read_text, round_robin, save_imported

GROUPS = ("components", "forms", "typography")
EXAMPLE = re.compile(r"\{\{<\s*example(?P<attrs>[^>]*)>\}\}(?P<code>.*?)\{\{<\s*/example\s*>\}\}", re.DOTALL)
GITHUB = "https://github.com/themesberg/flowbite/blob/main/content/"


def front_matter(text: str, key: str) -> str:
    found = re.search(rf"^{key}:\s*(.+)$", text, re.MULTILINE)
    return found.group(1).strip().strip("\"'") if found else ""


def sections(text: str) -> list[tuple[str, str]]:
    """Split a docs page into (heading, body) pairs at each '## ' heading."""
    parts = re.split(r"^##\s+(.+)$", text, flags=re.MULTILINE)
    return [(parts[i].strip(), parts[i + 1]) for i in range(1, len(parts) - 1, 2)]


def first_sentence(body: str) -> str:
    for paragraph in body.split("\n\n"):
        paragraph = paragraph.strip()
        if paragraph and not paragraph.startswith(("{{", "<", "```", "|", "-")):
            return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", " ".join(paragraph.split()))  # drop link URLs
    return ""


def page_entries(group: str, slug: str, text: str) -> list[Entry]:
    page_title = re.sub(r"^Tailwind CSS\s+|\s+-\s+Flowbite$", "", front_matter(text, "title"))
    page_description = front_matter(text, "description")
    entries = []
    used_ids: set[str] = set()
    for heading, body in sections(text):
        for number, match in enumerate(EXAMPLE.finditer(body), start=1):
            code = match.group("code").strip()
            if "{{" in code or "iframe" in match.group("attrs"):
                continue  # Hugo template code or full-page demos: not a self-contained snippet
            suffix = f" {number}" if number > 1 else ""
            entry_id = f"flowbite-{slug}-{slugify(heading)[:40].rstrip('-')}{'-' + str(number) if number > 1 else ''}"
            while entry_id in used_ids:  # a page can repeat a heading; keep both examples
                entry_id += "-b"
            used_ids.add(entry_id)
            entries.append(Entry(
                id=entry_id,
                title=f"{page_title}: {heading}{suffix} (Flowbite)",
                source="Flowbite",
                url=f"https://flowbite.com/docs/{group}/{slug}/#{slugify(heading)}",
                license="MIT",
                type="component",
                tags=[slug.removesuffix("s"), slug, group, "flowbite", "tailwind"],
                framework="tailwind",
                notes=f"{first_sentence(body) or page_description}\n\nOriginal file: {GITHUB}{group}/{slug}.md",
                code=code,
            ))
    return entries


def run(limit: int = 0, refresh: bool = False) -> tuple[int, int]:
    groups: dict[str, list[Entry]] = {}
    with open_repo("themesberg", "flowbite", refresh=refresh) as (archive, prefix):
        for group in GROUPS:
            for path in files_under(archive, f"{prefix}content/{group}/", r"^[^/]+\.md$"):
                slug = path.rsplit("/", 1)[1].removesuffix(".md")
                found = page_entries(group, slug, read_text(archive, path))
                if found:
                    groups[slug] = found
    print(f"{sum(len(v) for v in groups.values())} examples from {len(groups)} pages")
    return save_imported(round_robin(groups, limit))
