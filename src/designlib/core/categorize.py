"""Sort an entry into the library's categories and a platform (web / mobile / desktop).

Two steps, both explainable:

1. Rules. Every tag and title word is normalised and looked up in the taxonomy's
   keywords (core/taxonomy.py). Tags count more than title words, and an entry's
   first tag (a library's own folder, like Uiverse "button") counts most.
   Platform comes from clear signals: "mobile-app" -> mobile, "mac-app" -> desktop,
   web code / landing pages -> web, icons / colors / branding -> any.

2. Meaning (only for platform, only in the `categorize` command, only when the rules
   found nothing): the entry's description is compared with short descriptions of a
   mobile app, a website and a desktop app using the local semantic model. It decides
   only when one is clearly closer than the others; otherwise the platform stays "any".

Entries you categorised by hand (categories_manual) are never changed.
"""

import re
from collections import defaultdict

from designlib.core.schema import Entry, Platform
from designlib.core.taxonomy import BY_SLUG, CATEGORIES

MAX_CATEGORIES = 3

# Tags that say where something came from or how it's stored, not what it is.
IGNORED_TAGS = {"collectui", "uiverse", "hyperui", "designprompts", "prompt", "flowbite", "daisyui",
                "shadcn", "magicui", "tailwind", "tailwindcss", "react", "html", "css", "demo", "example",
                "video", "image", "inspiration", "lucide", "heroicons", "radix", "open-props", "svg"}

# ---------- keyword lookup ----------


def normalise(word: str) -> str:
    """'Buttons' -> 'button', 'Hero-Sections' -> 'hero-section'. Keeps 'glass', 'canvas'."""
    word = word.strip().lower()
    parts = []
    for part in word.split("-"):
        if len(part) > 3 and part.endswith("s") and not part.endswith(("ss", "us", "is")):
            part = part[:-1]
        parts.append(part)
    return "-".join(parts)


def _build_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for category in CATEGORIES:
        for keyword in (category.slug, *category.keywords):
            lookup.setdefault(normalise(keyword), category.slug)
    return lookup


KEYWORDS: dict[str, str] = _build_lookup()

# Library-specific knowledge that tags alone don't carry.
SOURCE_CATEGORY = {
    "Lucide": "icons",
    "Heroicons": "icons",
    "Radix Colors": "color",
    "Realtime Colors": "color",
    "SaaS Landing Page": "landing-page",
}
TYPE_CATEGORY = {"palette": "color", "token": "tokens"}


def _matches(term: str) -> list[str]:
    """Category slugs a tag or word points to: the whole term, then its hyphen parts."""
    term = normalise(term)
    if term in KEYWORDS:
        return [KEYWORDS[term]]
    return [KEYWORDS[part] for part in term.split("-") if part in KEYWORDS]


def categorize_categories(entry: Entry) -> list[str]:
    scores: dict[str, float] = defaultdict(float)

    if entry.source in SOURCE_CATEGORY:
        scores[SOURCE_CATEGORY[entry.source]] += 10
    if entry.type.value in TYPE_CATEGORY:
        scores[TYPE_CATEGORY[entry.type.value]] += 6

    tags = [t for t in entry.tags if t not in IGNORED_TAGS]
    for position, tag in enumerate(tags):
        whole = normalise(tag) in KEYWORDS
        weight = (5 if position == 0 else 3) if whole else 1  # a library's main tag counts most
        for slug in _matches(tag):
            scores[slug] += weight

    # The title, especially the part before ":" ("Pricing: Options with tier") or the
    # first words ("Button by ..."), names what the thing is.
    head = re.split(r"[:(]| by ", entry.title, maxsplit=1)[0]
    for word in re.findall(r"[a-z0-9-]+", head.lower()):
        for slug in _matches(word):
            scores[slug] += 2
    for word in re.findall(r"[a-z0-9-]+", entry.title.lower()):
        for slug in _matches(word):
            scores[slug] += 0.5

    if not scores:
        return ["other"]
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    best = ranked[0][1]
    # Keep strong matches only: at least 2 points and at least half of the best.
    chosen = [slug for slug, score in ranked if score >= 2 and score >= best / 2]
    # A design style says how something looks, not what it is ("Button in Botanical
    # style" is a button first), so it goes last when anything else matched.
    if "design-style" in chosen and len(chosen) > 1:
        chosen.remove("design-style")
        chosen = chosen[: MAX_CATEGORIES - 1] + ["design-style"]
    return chosen[:MAX_CATEGORIES] or ["other"]


# ---------- platform ----------

MOBILE = {"mobile-app", "mobile", "app-screens", "app-screen", "ios", "android", "dynamic-island", "wear-os",
          "watchos", "ipados", "material-3", "flutter", "jetpack-compose", "react-native",
          "splash-screen", "welcome-screen", "mobile-menu", "iphone", "watch", "widget-ios", "react-native"}
DESKTOP = {"mac-app", "macos", "desktop-app", "desktop", "windows-app", "tv-app", "tvos", "electron", "visionos"}
WEB = {"landing-page", "landing", "website", "web", "hero", "hero-section", "navbar", "footer", "footers",
       "framer", "webflow", "wordpress", "landing-section", "ai-sites", "agency", "portfolio", "saas",
       "web-animation", "scroll-animation", "next-js", "gatsby", "nuxt-js", "header-navigation"}
ANY_CATEGORIES = {"icons", "color", "tokens", "branding", "illustration", "fonts"}
# Libraries and kits made for phone apps: their HTML/React code is still mobile UI.
MOBILE_SOURCES = {"Framework7", "Konsta UI", "React Native Paper", "react-native-reusables",
                  "Compose samples", "Best Flutter UI Templates"}
WEB_SOURCES = {"SaaS Landing Page", "DesignPrompts", "Godly", "Land-book", "Awwwards", "Lapa Ninja"}


def platform_by_rules(entry: Entry, categories: list[str]) -> str | None:
    """'web' / 'mobile' / 'desktop' / 'any', or None when the rules can't tell."""
    tags = {normalise(t) for t in entry.tags} | {t.lower() for t in entry.tags}
    words = set(re.findall(r"[a-z0-9-]+", entry.title.lower()))
    if entry.source in MOBILE_SOURCES or entry.framework.value == "react-native":
        return "mobile"
    if categories and categories[0] in ANY_CATEGORIES:
        return "any"  # icons, colors, logos... work everywhere
    if entry.source in WEB_SOURCES or entry.framework.value in ("html", "tailwind", "react"):
        # Web code and website galleries are web, even an "iOS-style toggle" or a
        # landing page for a mobile app.
        return "web"
    if tags & MOBILE or {"ios", "ipados", "android", "iphone", "watchos", "wear"} & words:
        return "mobile"
    if tags & DESKTOP or {"macos", "desktop", "tvos", "visionos"} & words:
        return "desktop"
    if tags & WEB:
        return "web"
    return None


def categorize(entry: Entry) -> tuple[str, list[str]]:
    """Rules only (fast): used whenever an entry is saved."""
    categories = categorize_categories(entry)
    return platform_by_rules(entry, categories) or "any", categories


def apply(entry: Entry, force: bool = False) -> bool:
    """Fill in platform + categories unless you set them by hand. Returns True if changed."""
    if entry.categories_manual or (entry.categories and not force):
        return False
    platform, categories = categorize(entry)
    changed = (entry.platform.value, entry.categories) != (platform, categories)
    # pydantic doesn't convert on assignment, so build the enum ourselves
    entry.platform, entry.categories = Platform(platform), categories
    return changed


# ---------- meaning fallback for platform ----------

PROTOTYPES = {
    "mobile": "A mobile app screen on a phone: iOS or Android app UI, bottom tab bar, touch gestures, "
              "app onboarding, swipe cards, notch and status bar.",
    "web": "A website page in a browser: landing page, hero section, navigation bar, footer, "
           "marketing site, web app layout for desktop screens.",
    "desktop": "A desktop application window: macOS or Windows app, menu bar, window chrome, "
               "toolbar and sidebar panels, keyboard shortcuts.",
}
# How much closer the winner must be than the runner-up, per platform. Measured on the
# ~1,050 Collect UI shots whose platform the rules know (title labels and giveaway tags
# hidden): at these margins web was right 99%, mobile 96%, desktop 5/5 of the time.
# "Desktop" needs a big margin: with small ones it was right only 28% of the time.
MARGINS = {"web": 0.08, "mobile": 0.12, "desktop": 0.16}
MIN_SIMILARITY = 0.12


def caption(entry: Entry) -> str:
    """The words to judge the platform by: the title without a gallery's category prefix
    ("Landing Page, Hero by @x: our new site" -> "our new site"), as used to calibrate
    MARGINS, falling back to the full title."""
    text = re.split(r" by @[^:]*:?", entry.title, maxsplit=1)[-1].strip()
    return text or entry.title


def platform_by_meaning(texts: list[str]) -> list[str | None]:
    """For each text: 'web' / 'mobile' / 'desktop' when clearly closest, else None."""
    from designlib.core import semantic

    if not texts:
        return []
    names = list(PROTOTYPES)
    vectors = semantic.encode([PROTOTYPES[n] for n in names] + texts)
    protos, items = vectors[: len(names)], vectors[len(names):]
    results: list[str | None] = []
    for vector in items:
        sims = sorted(
            ((sum(a * b for a, b in zip(vector, proto)), name) for name, proto in zip(names, protos)),
            reverse=True,
        )
        (best, name), (second, _) = sims[0], sims[1]
        results.append(name if best >= MIN_SIMILARITY and best - second >= MARGINS[name] else None)
    return results


def labels(slugs: list[str]) -> list[str]:
    return [BY_SLUG[s].label for s in slugs if s in BY_SLUG]
