# Sources

Where references come from, what license applies, and what this library is allowed
to keep. **Store code** means component code may be saved in an entry (license recorded).
**Link only** means we keep the URL, title, tags, your notes and a hotlinked og:image
URL. Nothing else is copied.

Licenses were checked against each project's LICENSE file. Re-check before a big
import: licenses can change.

## Store code (open license)

| Source | License | Mode | Notes |
|---|---|---|---|
| [HyperUI](https://github.com/markmead/hyperui) | MIT | Store code | Tailwind v4 components. Importer: `designlib import hyperui` |
| [Uiverse galaxy](https://github.com/uiverse-io/galaxy) | MIT | Store code | HTML/CSS and Tailwind UI elements. Importer: `designlib import uiverse` |
| [shadcn/ui](https://github.com/shadcn-ui/ui) | MIT | Store code | React + Tailwind + Radix. Previews need a React build, so store as reference code |
| [Magic UI](https://github.com/magicuidesign/magicui) | MIT | Store code | Animated React components |
| [Flowbite](https://github.com/themesberg/flowbite) | MIT | Store code | Open-source core only. Flowbite Pro blocks are paid: link only |
| [daisyUI](https://github.com/saadeghi/daisyui) | MIT | Store code | Tailwind plugin; snippets need daisyUI CSS to render |
| [Open Props](https://github.com/argyleink/open-props) | MIT | Store code | CSS custom-property tokens |
| [Radix Colors](https://github.com/radix-ui/colors) | MIT | Store code | Accessible color scales |
| [Lucide](https://github.com/lucide-icons/lucide) | ISC | Store code | Icons |
| [Heroicons](https://github.com/tailwindlabs/heroicons) | MIT | Store code | Icons |
| [Aceternity UI](https://ui.aceternity.com) | Unclear | **Link only until checked** | Free components plus a paid Pro tier; terms are not a plain repo LICENSE. Ask before storing any code |

## Link only (inspiration galleries)

| Source | Mode | What it's good for |
|---|---|---|
| [Collect UI](https://collectui.com) | Link only | Daily UI shots grouped by component |
| [DesignPrompts](https://designprompts.dev) | Link only | Prompt ideas for AI-assisted design |
| [Godly](https://godly.website) | Link only | Bold, expressive marketing sites |
| [Land-book](https://land-book.com) | Link only | Landing pages by industry |
| [Lapa Ninja](https://www.lapa.ninja) | Link only | Landing pages and free resources |
| [SaaS Landing Page](https://saaslandingpage.com) | Link only | SaaS page sections |
| [Awwwards](https://www.awwwards.com) | Link only | Award-winning, experimental sites |
| [Realtime Colors](https://www.realtimecolors.com) | Link only | Trying palettes and type on a live page |

## Rules this library follows

- Code is only stored when the license is MIT, Apache-2.0, ISC, or your own work (`Own`).
  The schema rejects anything else.
- Images from gallery sites are never downloaded. Only `og:image` URLs are kept and
  shown as hotlinks. Your own screenshots go in `library/assets/mine/`.
- Fetching checks `robots.txt`, sends an honest User-Agent, waits 2 s between requests
  to the same site, and reads metadata only.
