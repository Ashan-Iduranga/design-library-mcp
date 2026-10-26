"""Import real mobile app designs from open-source sample apps, as screenshot references:

  Compose samples           (github.com/android/compose-samples, Apache-2.0)
      Google's official Jetpack Compose apps (Jetnews, Jetchat, Reply, Jetsnack, ...).
      One entry per app folder that has a screenshots/ directory.
  Best Flutter UI Templates (github.com/mitesh77/Best-Flutter-UI-Templates, MIT)
      Flutter app templates (hotel booking, fitness, design course, ...), one per GIF in assets/.

The screenshots/GIFs are shown straight from GitHub (both licenses allow it). The apps'
code is linked, not stored: each is a whole project, not a snippet.
"""

import re

from designlib.core.schema import Entry
from designlib.importers.common import files_under, open_repo, read_text, save_imported, title_case

COMPOSE_RAW = "https://raw.githubusercontent.com/android/compose-samples/main/"
COMPOSE_TREE = "https://github.com/android/compose-samples/tree/main/"
FLUTTER_RAW = "https://raw.githubusercontent.com/mitesh77/Best-Flutter-UI-Templates/master/"
FLUTTER_REPO = "https://github.com/mitesh77/Best-Flutter-UI-Templates"


def first_paragraph(markdown: str) -> str:
    """The first real sentence block of a README (skips headings, images, badges)."""
    for block in markdown.split("\n\n"):
        block = block.strip()
        if block and not block.startswith(("#", "!", "[!", "<", "|", "```")):
            return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", " ".join(block.split()))[:600]
    return ""


def pick_screenshot(paths: list[str]) -> str | None:
    """Prefer an animated demo, then an overview image, then anything."""
    for preferred in (r"\.gif$", r"screenshots?\.png$", r"_all_screens", r"\.(png|jpg)$"):
        for path in paths:
            if re.search(preferred, path, re.IGNORECASE):
                return path
    return None


def compose_entries(archive, prefix: str) -> list[Entry]:
    entries = []
    apps = sorted({p.removeprefix(prefix).split("/")[0] for p in files_under(archive, prefix, r"^[^/]+/screenshots/")})
    for app in apps:
        shots = [p.removeprefix(prefix) for p in files_under(archive, f"{prefix}{app}/screenshots/")]
        shot = pick_screenshot(shots)
        readme = prefix + f"{app}/README.md"
        about = first_paragraph(read_text(archive, readme)) if readme in archive.namelist() else ""
        entries.append(Entry(
            id=f"compose-{app.lower()}",
            title=f"{app}: Jetpack Compose sample app (Android)",
            source="Compose samples",
            url=COMPOSE_TREE + app,
            license="Apache-2.0",
            type="screen",
            tags=[app.lower(), "jetpack-compose", "android", "material-3", "kotlin", "mobile-app"],
            framework="none",
            notes=f"{about}\n\nOfficial Android sample by Google, built with Jetpack Compose and Material 3. "
                  f"Full source (Kotlin) at the link.",
            preview_image_url=COMPOSE_RAW + shot if shot else None,
        ))
    return entries


def flutter_entries(archive, prefix: str) -> list[Entry]:
    entries = []
    for path in files_under(archive, prefix + "assets/", r"^[^/]+\.gif$"):
        name = path.rsplit("/", 1)[1].removesuffix(".gif")
        label = title_case(name)
        entries.append(Entry(
            id=f"flutter-template-{name.replace('_', '-')}",
            title=f"{label}: Flutter app template",
            source="Best Flutter UI Templates",
            url=FLUTTER_REPO,
            license="MIT",
            type="screen",
            tags=[name.replace("_", "-"), "flutter", "dart", "mobile-app", "animation"],
            framework="none",
            notes=f"{label} screens from Best Flutter UI Templates (free, MIT): a Flutter UI with "
                  f"animations. Full Dart source in the repository.",
            preview_image_url=FLUTTER_RAW + path.removeprefix(prefix),
        ))
    return entries


def run(limit: int = 0, refresh: bool = False) -> tuple[int, int]:
    with open_repo("android", "compose-samples", license="Apache-2.0", refresh=refresh) as (archive, prefix):
        entries = compose_entries(archive, prefix)
    with open_repo("mitesh77", "Best-Flutter-UI-Templates", branch="master", refresh=refresh) as (archive, prefix):
        entries += flutter_entries(archive, prefix)
    print(f"{len(entries)} sample apps and templates")
    return save_imported(entries[:limit] if limit > 0 else entries)
