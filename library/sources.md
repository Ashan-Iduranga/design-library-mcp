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

## Mobile app libraries and references

| Source | License | Entries | Import command | Notes |
|---|---|---|---|---|
| [Framework7](https://github.com/framework7io/framework7) | MIT | 53 | `import framework7` | Kitchen-sink screens rendered live as phones, iOS / Material theme switch. 50 pages that only work inside the running app are skipped |
| [Konsta UI](https://github.com/konstaui/konsta) | MIT | 36 | `import konsta` | Tailwind mobile components (iOS + Material), React code |
| [React Native Paper](https://github.com/callstack/react-native-paper) | MIT | 37 | `import reactnative` | Material 3 for React Native, with install command |
| [react-native-reusables](https://github.com/founded-labs/react-native-reusables) | MIT | 32 | `import reactnative` | shadcn/ui for React Native (Nativewind), `npx @react-native-reusables/cli@latest add <name>` |
| [Compose samples](https://github.com/android/compose-samples) | Apache-2.0 | 6 | `import nativeapps` | Google's official Android apps (Jetnews, Jetchat, Reply...), screenshots + link to code |
| [Best Flutter UI Templates](https://github.com/mitesh77/Best-Flutter-UI-Templates) | MIT | 5 | `import nativeapps` | Flutter app templates, animated GIFs + link to code |
| [Penpot community library](https://penpot.app/penpothub/libraries-templates) | CC BY 4.0 | 124 | `import penpot` | Free UI kits / templates (.penpot), link-only with preview image. Credit the author when you reuse one |
| [Material Design 3](https://m3.material.io) | link only | 47 | `import guidelines` | Component overviews, foundations and styles (robots.txt allows; found via its sitemap) |
| [Apple HIG](https://developer.apple.com/design/human-interface-guidelines) | link only | 170 | `import guidelines` | Every HIG page, via Apple's documentation index |
| [Apple Design Resources](https://developer.apple.com/design/resources/) | link only | 15 | `import guidelines` | Official Figma UI kits (iOS, iPadOS, macOS, watchOS, visionOS, app icons...). Apple's terms apply |
| [Wear OS design kits](https://developer.android.com/design/ui/wear/guides/get-started/design-kits) | link only | 2 | `import guidelines` | Official Figma kits for apps and tiles |
| [MD3 Sketch kit (Hxly)](https://www.sketchappsources.com/free-source/4784-md3-material-design-3-ui-kit-sketch-freebie-resource.html) | link only | 1 | `import guidelines` | Free community Sketch port of Material 3; no license stated |
| [material-3-skill](https://github.com/hamen/material-3-skill) | MIT | style guides | (copied once) | `library/styles/material-3*.md`: Material 3 rules for `get_style_guide`, credited |

## Inspiration galleries (link only)

| Source | Entries | How it's collected | Notes |
|---|---|---|---|
| [SaaS Landing Page](https://saaslandingpage.com) | ~847 | `import saaslandingpage`: its sitemap, one polite page fetch each | robots.txt allows it. Each page's own tags, technologies and fonts are kept. Its **templates are paid and skipped** |
| [DesignPrompts](https://designprompts.dev) | ~890 | `import designprompts`: its sitemap, one polite page fetch each | robots.txt allows it (including AI user agents). One entry per style and per style × component |
| [Collect UI](https://collectui.com) | 3,633 (full catalogue, 26 Oct 2026) | `import collectui` | No public API or sitemap. The importer reads the site's own data backend with the public key from its JavaScript, 200 designs per request, 2 s apart. **You chose this (26 Oct 2026); it's not a documented public interface.** Each entry links to the designer's original post |
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
| [github.com/penpot/penpot](https://github.com/penpot/penpot) | The Penpot design tool itself (MPL-2.0), not designs. Its community library is imported instead |
| [github.com/topics/mobile-development](https://github.com/topics/mobile-development) | Code frameworks and tutorials (Flutter, React Native, ML), not design references |
| [Awesome-UI-Templates](https://github.com/KKshitiz/Awesome-UI-Templates) | No license, unmaintained since 2021, only links to Dribbble shots |
| [Mockplus Material 3 kit](https://www.mockplus.com/example/rp/58) | One kit in Mockplus's proprietary .rp format, no terms; Material 3 is covered by the sources above |
| [Aceternity UI](https://ui.aceternity.com) | Free components plus a paid Pro tier, and its terms aren't a plain open-source LICENSE file. Ask before storing any code |

## Rules this library follows

- Code is only stored when the license is MIT, Apache-2.0, ISC, or your own work (`Own`).
  The schema rejects anything else.
- Images from gallery sites are never downloaded. Only preview-image URLs are kept and
  shown as hotlinks (no referrer). Your own screenshots go in `library/assets/mine/`.
- Website fetching checks `robots.txt` (once per site), sends an honest User-Agent,
  waits 2 s between requests to the same site, and reads metadata only.
