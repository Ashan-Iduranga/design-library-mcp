# design-library-mcp

A local, free, open-source design-reference library with two faces:

- a **web gallery** at http://127.0.0.1:8000 where you browse, search, preview and curate references, and
- an **MCP server** that Claude queries, so UI work starts from references you chose on purpose
  instead of generic defaults.

Everything runs on your machine. No API keys, no paid services, no cloud.

```
library/entries/*.json  ──►  library/index.db (SQLite + FTS5)   ──►  CLI · web gallery · MCP server
   source of truth             library/vectors.db (sqlite-vec)        one shared `core` package
                               rebuildable caches
```

Search is **hybrid**: keyword matching (FTS5) merged with **semantic** matching, so
"spinner while waiting" finds a loader and "choose a plan" finds pricing tables even with no
shared words. The meaning model (`all-MiniLM-L6-v2`) runs locally on your CPU.

---

## 1. Install (once)

Needs Python 3.11+ (you have 3.14) and [uv](https://docs.astral.sh/uv/) (free, open source).

```powershell
python -m pip install --user uv
cd "D:\C Skills\design-library-mcp"
python -m uv sync            # creates .venv and installs everything (incl. semantic search)
python -m uv run python -m designlib rebuild   # builds the search index + meaning vectors
python -m uv run pytest -m "not slow"          # optional: tests, about 8 seconds
```

The first `rebuild` (or first search) downloads the meaning model once: about 90 MB from
Hugging Face, free, no account. After that it works offline. Semantic search pulls in PyTorch
(CPU build, a few hundred MB). To install without it: `python -m uv sync --no-group semantic`;
search then uses keywords only and everything else works the same.

> `uv` lives in `C:\Users\user\AppData\Roaming\Python\Python314\Scripts`, which isn't on
> your PATH, so this README writes `python -m uv`. Add that folder to PATH to type `uv` instead.

## 2. Start the gallery

Double-click **`start.cmd`**, or in PowerShell:

```powershell
cd "D:\C Skills\design-library-mcp"
.\start.ps1
```

Both open http://127.0.0.1:8000 in your browser. Stop with **Ctrl+C**.
If PowerShell says running scripts is disabled, use `start.cmd`, which doesn't need PowerShell.

The gallery only listens on `127.0.0.1`, so other devices on your network cannot reach it.

**You usually don't need to start it yourself:** while Claude is open, the MCP server also
serves the gallery, so the `gallery_url` links Claude gives you always open. If the gallery is
already running (started by Claude or by you), `start.cmd` just opens it in your browser.

## 3. Connect Claude

The MCP server is started by Claude itself. You never run it by hand. Both setups below use
the project's own Python (`.venv\Scripts\python.exe`), so they don't depend on PATH.

### (a) Claude desktop app (Windows)

1. Open the config file. In the app: **Settings → Developer → Edit Config**, or open it directly:
   `%APPDATA%\Claude\claude_desktop_config.json`
   (on this PC: `C:\Users\user\AppData\Roaming\Claude\claude_desktop_config.json`).
2. Add a `design-library` entry inside `"mcpServers"`, next to any servers already there:

   ```json
   {
     "mcpServers": {
       "design-library": {
         "command": "D:\\C Skills\\design-library-mcp\\.venv\\Scripts\\python.exe",
         "args": ["-m", "designlib", "mcp"]
       }
     }
   }
   ```

   In JSON every backslash in a path is written twice (`\\`).
3. **Quit Claude completely** (system tray icon → Quit, not just closing the window) and reopen it.
4. In a new chat, open the tools/connectors menu: **design-library** should be listed with 6 tools.

> Already done on this PC (26 Oct 2026). The original file was backed up to
> `claude_desktop_config.json.backup-2026-10-26` in the same folder.

### (b) Claude Code

```powershell
claude mcp add --scope user design-library -- "D:\C Skills\design-library-mcp\.venv\Scripts\python.exe" -m designlib mcp
```

- `--scope user` makes it available in every project. Leave it out to add it only to the
  current project.
- Check it: `claude mcp get design-library` should say **✔ Connected**. Inside Claude Code, `/mcp` lists it.
- Remove it: `claude mcp remove design-library -s user`

> Already done on this PC (26 Oct 2026).

### Make Claude use it every time (optional)

Claude reads the server's built-in instructions, but a line in your global
`C:\Users\user\.claude\CLAUDE.md` makes it a habit in Claude Code:

```markdown
Before designing or building any UI, query the `design-library` MCP server
(search_designs, then get_design; check list_styles / get_style_guide) and say which references you used.
```

### Things to ask Claude

- "Build a pricing section for my app. Check my design library first."
- "What toggles do I have saved? Show me the one I rated highest."
- "Use my *quiet-product* style guide to restyle this settings page."
- "Save https://example.com/some-landing-page to my design library as a screen, tagged hero, saas."

## 4. The MCP tools

| Tool | Use |
|---|---|
| `search_designs(query, type?, tags?, framework?, limit=10, mode="hybrid")` | Ranked matches (no code) with `gallery_url` for each. `mode="keyword"` = exact words only |
| `get_design(id)` | The full entry: code (when the license allows), style notes, when to use / avoid, license, `gallery_url` |
| `list_tags()` | Tags and how many entries use each |
| `list_styles()` | Your style guides in `library/styles/` |
| `get_style_guide(style)` | One guide's rules (palette, type, spacing, do/don't) |
| `add_design(url, type, tags?, notes?)` | Save a page as a link-only reference (metadata only) |

`gallery_url` (http://127.0.0.1:8000/d/&lt;id&gt;) opens whenever Claude or `start.cmd` is running:
the MCP server serves the gallery in the background if port 8000 is free. With several Claude
sessions, the first one serves it; if that one closes, another takes over within 30 seconds.
To turn this off, set the environment variable `DESIGNLIB_GALLERY_WITH_MCP=0`.

### How semantic search behaves

- The gallery and the MCP server load the model **in the background** when they start
  (importing PyTorch takes ~10 s). Until then, searches use keywords only, so the gallery's
  live search never waits. Once ready, the result count says *matched by meaning and keywords*.
  Claude's searches wait for the model, so they always include meaning.
- Each entry's title, type, tags, notes, style notes and when to use / avoid are embedded.
  Code is left out on purpose (class names would drown the description).
- New or edited entries are embedded automatically before the next semantic search. Only
  entries whose text changed are re-embedded; toggling a favorite costs nothing.
- Results from both methods are merged with Reciprocal Rank Fusion: an entry found by both
  keywords and meaning ranks highest. Matches weaker than a cosine distance of 0.75 are dropped.
- Turn it off without uninstalling: set the environment variable `DESIGNLIB_SEMANTIC=0`.

## 5. Command line

```powershell
python -m uv run python -m designlib <command>
```

| Command | Example |
|---|---|
| `add` | `add https://godly.website --type style --tags bold,editorial --notes "big type" --rating 4` |
| `list` | `list --type component --limit 20` |
| `search` | `search pricing table --tags saas --framework tailwind` (add `--keyword` for exact words only) |
| `rebuild` | `rebuild` (recreate `index.db` from the JSON files, embed new/changed entries) |
| `serve` | `serve --open` (`--port 8001`, `--reload` while developing) |
| `import` | `import hyperui --limit 60`, `import uiverse --category buttons,cards --limit 100` |
| `mcp` | Used by Claude; waits silently for a client |

`add` options: `--title`, `--framework`, `--rating 1-5`, `--favorite`, `--no-fetch` (don't contact the site).

## 6. Your library

- **Entries**: `library/entries/<id>.json`, one file per reference. Edit them in the gallery
  (or by hand, then run `rebuild`). Commit them with git like any other file.
- **Screenshots**: uploaded in the gallery, stored in `library/assets/mine/`.
- **Style guides**: add `library/styles/<name>.md`. The first paragraph becomes the summary
  Claude sees in `list_styles`. Start from `quiet-product.md`.
- **Sources**: `library/sources.md` lists every source, its license, and whether code may be stored.

An entry has: `id, title, source, url, license, type (style|component|screen|interaction|layout|palette|token),
tags, framework (html|tailwind|react|none), style_notes {palette, fonts, spacing, mood}, notes, code, prompt,
preview_image_url, local_image, when_to_use, avoid_when, my_rating (1-5), favorite, added_at, updated_at`.

### The rules it enforces

- **Code is only stored for MIT, Apache-2.0, ISC or your own work (`Own`).** The schema rejects anything else,
  whether it comes from the CLI, the gallery or Claude.
- **Gallery and inspiration sites are link only**: URL, title, tags, your notes, and the og:image *URL*
  (shown as a hotlink with no referrer). Their images and content are never downloaded.
- **Fetching is polite**: checks `robots.txt`, sends an honest User-Agent, waits 2 s between requests to
  the same site, reads at most 1 MB, and only reads metadata.
- **Importers verify the repo's LICENSE file** before reading anything, and stop if it isn't open.

## 7. Project layout

```
design-library-mcp/
  start.cmd / start.ps1 / start.sh   start the gallery
  pyproject.toml, uv.lock            dependencies
  docs/testing.md                    tests + MCP Inspector walkthrough
  library/                           YOUR DATA (entries, assets, styles, sources.md)
  src/designlib/
    config.py                        paths, 127.0.0.1:8000
    cli.py                           the command line
    core/                            schema, storage, index, search, semantic, fetch, library, styleguide
    web/                             FastAPI app, Jinja templates, CSS/JS, vendored assets
    importers/                       hyperui.py, uiverse.py, common.py
    mcp_server.py                    the MCP tools
  tests/                             pytest suite
```

## 8. Troubleshooting

| Problem | Fix |
|---|---|
| Claude desktop doesn't show design-library | Fully quit and reopen the app. Check the JSON is valid (doubled backslashes, commas). Logs: `%APPDATA%\Claude\logs\mcp-server-design-library.log` |
| `claude mcp get` says failed | Run `"D:\C Skills\design-library-mcp\.venv\Scripts\python.exe" -m designlib mcp` yourself: it should sit silently. Any error it prints is the cause |
| `.venv` missing or broken | `python -m uv sync` |
| Search misses something you just edited by hand | `python -m uv run python -m designlib rebuild` |
| Gallery never says "matched by meaning" | Check `python -m uv run python -c "from designlib.core import semantic; print(semantic.enabled())"` prints True; run `rebuild` once to download the model |
| Semantic search acting strange | Delete `library/vectors.db`; it is rebuilt on the next search |
| A `gallery_url` link doesn't open | Is Claude (or `start.cmd`) running? The gallery lives as long as one of them does. After updating this project, restart Claude (desktop: tray → Quit; Claude Code: `/mcp` → reconnect) so it runs the new code |
| Port 8000 used by another program | Set the environment variable `DESIGNLIB_PORT=8001` (for Claude too: add `"env": {"DESIGNLIB_PORT": "8001"}` to the desktop config entry), or run `serve --port 8001` |
| Test the tools interactively | See [docs/testing.md](docs/testing.md) (MCP Inspector) |

## Credits and licenses

This project: MIT (see `LICENSE`). Third-party files stored in the project (`src/designlib/web/static/vendor/`),
each with its license file: htmx 2.0.4 (0BSD), Tailwind CSS browser build 4.1.11 (MIT),
highlight.js 11.10.0 (BSD-3-Clause), Familjen Grotesk font (SIL OFL 1.1).
Semantic search uses sentence-transformers (Apache-2.0), sqlite-vec (MIT/Apache-2.0) and the
all-MiniLM-L6-v2 model (Apache-2.0), downloaded at first use rather than stored in the repo.
Imported components keep their source's license (HyperUI: MIT, Uiverse: MIT) and a link to the
original file in each entry.
