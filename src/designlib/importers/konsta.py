"""Import Konsta UI's examples (github.com/konstaui/konsta, MIT).

Konsta UI is a set of mobile components built with Tailwind CSS that look native on iOS
and Android (Material). Its kitchen sink has one React page per component:
  kitchen-sink/react/pages/<Name>.jsx
They're stored as React code (no live preview: they need the Konsta React package).
"""

import re

from designlib.core.schema import Entry
from designlib.importers.common import files_under, open_repo, read_text, save_imported

PAGES = "kitchen-sink/react/pages/"
GITHUB = "https://github.com/konstaui/konsta/blob/master/" + PAGES


def words(name: str) -> str:
    """'ActionSheet' -> 'Action Sheet'"""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)


def build_entry(name: str, code: str) -> Entry:
    label = words(name)
    slug = label.lower().replace(" ", "-")
    return Entry(
        id=f"konsta-{slug}",
        title=f"{label} (Konsta UI, iOS + Material)",
        source="Konsta UI",
        url=f"https://konstaui.com/react/{slug}",
        license="MIT",
        type="component",
        tags=[slug, "konsta", "tailwind", "ios", "material", "mobile-app"],
        framework="react",
        notes=f"Konsta UI {label} example: mobile components made with Tailwind CSS that follow iOS and "
              f"Material Design (Android) look and feel.\n\nUse: npm i konsta (React, Vue or Svelte). "
              f"Docs: https://konstaui.com\n\nOriginal file: {GITHUB}{name}.jsx",
        code=code.strip(),
    )


def run(limit: int = 0, refresh: bool = False) -> tuple[int, int]:
    with open_repo("konstaui", "konsta", branch="master", refresh=refresh) as (archive, prefix):
        entries = [
            build_entry(path.rsplit("/", 1)[1].removesuffix(".jsx"), read_text(archive, path))
            for path in files_under(archive, prefix + PAGES, r"^[^/]+\.jsx$")
        ]
    print(f"{len(entries)} Konsta UI examples")
    return save_imported(entries[:limit] if limit > 0 else entries)
