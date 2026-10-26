"""Import React Native component libraries (stored as code, framework "react-native"):

  React Native Paper     (github.com/callstack/react-native-paper, MIT)
      Material Design 3 for React Native. Examples: example/src/Examples/<Name>Example.tsx
  react-native-reusables (github.com/founded-labs/react-native-reusables, MIT)
      shadcn/ui-style components for React Native (Nativewind).
      Components: packages/registry/src/nativewind/components/ui/<name>.tsx

Each entry carries the install command so Claude Code can add the real component.
"""

import re

from designlib.core.schema import Entry
from designlib.importers.common import files_under, open_repo, read_text, save_imported

PAPER_EXAMPLES = "example/src/Examples/"
PAPER_GITHUB = "https://github.com/callstack/react-native-paper/blob/main/" + PAPER_EXAMPLES
REUSABLES_UI = "packages/registry/src/nativewind/components/ui/"
REUSABLES_GITHUB = "https://github.com/founded-labs/react-native-reusables/blob/main/" + REUSABLES_UI


def words(name: str) -> str:
    """'BottomNavigationBar' -> 'Bottom Navigation Bar'"""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name)


def paper_entry(name: str, code: str) -> Entry:
    label = words(name)
    slug = label.lower().replace(" ", "-")
    return Entry(
        id=f"rnpaper-{slug}",
        title=f"{label} (React Native Paper, Material 3)",
        source="React Native Paper",
        url=PAPER_GITHUB + f"{name}Example.tsx",
        license="MIT",
        type="component",
        tags=[slug, "react-native-paper", "material-3", "react-native", "android", "ios"],
        framework="react-native",
        notes=f"React Native Paper {label} example: Material Design 3 components for React Native "
              f"(Android and iOS).\n\nInstall: npm install react-native-paper react-native-safe-area-context. "
              f"Docs: https://reactnativepaper.com",
        code=code.strip(),
        prompt="npm install react-native-paper react-native-safe-area-context",
    )


def reusables_entry(name: str, code: str) -> Entry:
    label = name.replace("-", " ").title()
    install = f"npx @react-native-reusables/cli@latest add {name}"
    return Entry(
        id=f"rnreusables-{name}",
        title=f"{label} (react-native-reusables)",
        source="react-native-reusables",
        url=f"https://reactnativereusables.com/docs/components/{name}",
        license="MIT",
        type="component",
        tags=[name, "react-native-reusables", "shadcn", "nativewind", "react-native"],
        framework="react-native",
        notes=f"{label} from react-native-reusables: shadcn/ui-style components for React Native, styled "
              f"with Nativewind (Tailwind).\n\nInstall into a project: {install}\n\n"
              f"Original file: {REUSABLES_GITHUB}{name}.tsx",
        code=code.strip(),
        prompt=install,
    )


def run(limit: int = 0, refresh: bool = False) -> tuple[int, int]:
    entries: list[Entry] = []
    with open_repo("callstack", "react-native-paper", refresh=refresh) as (archive, prefix):
        for path in files_under(archive, prefix + PAPER_EXAMPLES, r"^[^/]+Example\.tsx$"):
            name = path.rsplit("/", 1)[1].removesuffix("Example.tsx")
            entries.append(paper_entry(name, read_text(archive, path)))
    with open_repo("founded-labs", "react-native-reusables", refresh=refresh) as (archive, prefix):
        for path in files_under(archive, prefix + REUSABLES_UI, r"^[^/]+\.tsx$"):
            entries.append(reusables_entry(path.rsplit("/", 1)[1].removesuffix(".tsx"), read_text(archive, path)))
    print(f"{len(entries)} React Native components and examples")
    return save_imported(entries[:limit] if limit > 0 else entries)
