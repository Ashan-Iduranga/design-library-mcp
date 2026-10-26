# Sources

Where references come from, what license applies, and what this library is allowed
to keep. **Code** means component code is stored in the entry (license recorded).
**Link only** means we keep the URL, title, tags, notes and a hotlinked preview-image
URL. Nothing else is copied.

Licenses were checked against each project's LICENSE file at import time (the importers
re-check on every run and stop if a license isn't open).

## Code libraries (imported in full, with code)

| Source | License | Entries | Import command | Notes |
|---|---|---|---|---|
| [HyperUI](https://github.com/markmead/hyperui) | MIT | 552 | `import hyperui --dark` | Tailwind v4 components, light + dark variants. Live previews |
| [Uiverse galaxy](https://github.com/uiverse-io/galaxy) | MIT | 3,802 | `import uiverse` | HTML/CSS and Tailwind elements, each credited to its author. Live previews |
| [shadcn/ui](https://github.com/shadcn-ui/ui) | MIT | 397 | `import shadcn` | UI components, blocks, charts, examples (React). Entries include `npx shadcn@latest add <name>` |
| [Magic UI](https://github.com/magicuidesign/magicui) | MIT | 248 | `import magicui` | Animated React components + examples. Entries include the install command |
| [Flowbite](https://github.com/themesberg/flowbite) | MIT | 471 | `import flowbite` | Open-source docs examples only. Flowbite Pro / Blocks are paid and never touched. Previews load Flowbite's theme + JS |
| [daisyUI](https://github.com/saadeghi/daisyui) | MIT | 519 | `import daisyui` | Component examples. Previews load daisyUI's CSS |
| [Open Props](https://github.com/argyleink/open-props) | MIT | 37 | `import tokens` | CSS custom-property tokens; color scales shown as swatches |
| [Radix Colors](https://github.com/radix-ui/colors) | MIT | 31 | `import tokens` | 12-step light + dark color scales |
| [Lucide](https://github.com/lucide-icons/lucide) | ISC | 42 | `import icons` | One entry per category (1,903 icons), every icon name listed and previewed |
| [Heroicons](https://github.com/tailwindlabs/heroicons) | MIT | 4 | `import icons` | One entry per style (outline, solid, mini, micro) |

`python -m designlib import all` re-imports every code library above. Re-imports keep
your own ratings, favorites and notes.

## Inspiration galleries (link only)

| Source | Entries | How it's collected | Notes |
|---|---|---|---|
| [SaaS Landing Page](https://saaslandingpage.com) | ~847 | `import saaslandingpage`: its sitemap, one polite page fetch each | robots.txt allows it. Each page's own tags, technologies and fonts are kept. Its **templates are paid and skipped** |
| [DesignPrompts](https://designprompts.dev) | ~890 | `import designprompts`: its sitemap, one polite page fetch each | robots.txt allows it (including AI user agents). One entry per style and per style × component |
| [Collect UI](https://collectui.com) | 60 of 3,631 so far | `import collectui` | No public API or sitemap. The importer reads the site's own data backend with the public key from its JavaScript, 200 designs per request, 2 s apart. **You chose this (26 Oct 2026); it's not a documented public interface.** Each entry links to the designer's original post |
| [Godly](https://godly.website) | 1 | added by hand | robots.txt blocks AI agents by name (`ai-train=no`). Not bulk-collected |
| [Awwwards](https://www.awwwards.com) | 0 | add by hand | robots.txt disallows `/gallery/`, `/websites/?`, `/elements/`. Not bulk-collected |
| [Land-book](https://land-book.com) | 1 | added by hand | Bot protection returns 403. Not bulk-collected |
| [Lapa Ninja](https://www.lapa.ninja) | 0 | add by hand | Bot protection returns 403 (even for robots.txt). Not bulk-collected |
| [Realtime Colors](https://www.realtimecolors.com) | 1 | added by hand | A tool, not a catalogue |

Single pages from any site can always be added by hand: in the gallery (Add reference),
with `python -m designlib add <url>`, or by asking Claude (`add_design`).

## Not imported

| Source | Why |
|---|---|
| [Aceternity UI](https://ui.aceternity.com) | Free components plus a paid Pro tier, and its terms aren't a plain open-source LICENSE file. Ask before storing any code |

## Rules this library follows

- Code is only stored when the license is MIT, Apache-2.0, ISC, or your own work (`Own`).
  The schema rejects anything else.
- Images from gallery sites are never downloaded. Only preview-image URLs are kept and
  shown as hotlinks (no referrer). Your own screenshots go in `library/assets/mine/`.
- Website fetching checks `robots.txt` (once per site), sends an honest User-Agent,
  waits 2 s between requests to the same site, and reads metadata only.
