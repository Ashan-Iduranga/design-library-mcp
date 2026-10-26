"""`designlib categorize`: sort the whole library into categories and platforms.

Runs the rules from core/categorize.py on every entry (skipping ones you categorised by
hand), then asks the meaning model about the platform of entries the rules couldn't
place, saves what changed, rebuilds the index and prints a coverage report.
"""

from collections import Counter, defaultdict

from designlib.core import categorize, semantic
from designlib.core.index import rebuild_index
from designlib.core.schema import Platform
from designlib.core.storage import iter_entries, save_entry


def run(force: bool = False, use_meaning: bool = True) -> str:
    entries = list(iter_entries())
    changed = []
    unsure = []  # entries whose platform the rules couldn't tell

    for entry in entries:
        if entry.categories_manual:
            continue
        before = (entry.platform, list(entry.categories))
        if force or not entry.categories:
            entry.categories = categorize.categorize_categories(entry)
        if force or not entry.categories or entry.platform == Platform.any:
            rule = categorize.platform_by_rules(entry, entry.categories)
            if rule is None:
                unsure.append(entry)
            entry.platform = Platform(rule or "any")
        if (entry.platform, entry.categories) != before:
            changed.append(entry)

    decided = 0
    if use_meaning and unsure and semantic.enabled():
        print(f"Asking the meaning model about the platform of {len(unsure)} entries...")
        verdicts = categorize.platform_by_meaning([categorize.caption(e) for e in unsure])
        for entry, verdict in zip(unsure, verdicts):
            if verdict:
                entry.platform = Platform(verdict)
                decided += 1
                if entry not in changed:
                    changed.append(entry)

    for entry in changed:
        save_entry(entry, touch=False)  # categories aren't an "edit", so keep updated_at
    rebuild_index()
    return report(entries, len(changed), len(unsure), decided)


def report(entries, changed: int, unsure: int, decided: int) -> str:
    total = len(entries)
    platforms = Counter(e.platform.value for e in entries)
    in_other = defaultdict(int)
    per_source = Counter(e.source for e in entries)
    for e in entries:
        if e.categories == ["other"]:
            in_other[e.source] += 1
    lines = [
        f"{total:,} entries, {changed:,} updated.",
        "Platforms: " + ", ".join(f"{p} {n:,}" for p, n in platforms.most_common()),
        f"Platform decided by the meaning model: {decided:,} of {unsure:,} the rules couldn't place.",
        f"In a real category: {1 - sum(in_other.values()) / max(total, 1):.1%} "
        f"({sum(in_other.values()):,} left in Other)",
    ]
    for source, count in sorted(in_other.items(), key=lambda x: -x[1]):
        lines.append(f"  Other in {source}: {count} of {per_source[source]}")
    return "\n".join(lines)
