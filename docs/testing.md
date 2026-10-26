# Testing

All commands run from the project folder:

```powershell
cd "D:\C Skills\design-library-mcp"
```

> `uv` was installed with `pip install --user`, so it is called as `python -m uv`.
> If you add `C:\Users\user\AppData\Roaming\Python\Python314\Scripts` to your PATH,
> you can type `uv` instead of `python -m uv` everywhere below.

## 1. Automated tests (pytest)

```powershell
python -m uv run pytest -m "not slow"                     # everything except the real-model test (~8 s)
python -m uv run pytest                                   # everything (~18 s: loads PyTorch once)
python -m uv run pytest -q tests/test_web.py              # one file
python -m uv run pytest -k "license"                      # tests whose name contains "license"
python -m uv run pytest --cov=designlib --cov-report=term-missing   # with line coverage
```

No test touches the internet or your real library (the `slow` test uses the model only if it's
already downloaded, otherwise it is skipped). `tests/conftest.py` points every
test at an empty temporary library (`DESIGNLIB_LIBRARY`), web fetches use
`httpx.MockTransport`, and importer tests build small fake repo zips in memory.

| File | What it checks |
|---|---|
| `test_schema.py` | Validation rules: code only with an open license, rating 1-5, safe ids, tag cleanup, screenshots stay in `assets/mine/` |
| `test_storage_index.py` | JSON files are the source of truth; the index rebuilds from them; broken files are skipped |
| `test_search.py` | Full-text search, prefix and plural matching, every filter and sort, FTS syntax can't crash it |
| `test_fetch.py` | robots.txt is respected, honest User-Agent, 2 s per-host delay, 1 MB read cap, HTML only |
| `test_cli.py` | `add`, `list`, `search`, `rebuild` |
| `test_web.py` | Every gallery route (FastAPI `TestClient`): HTMX partials, filters, sandboxed previews, add/edit/delete, uploads, favorites |
| `test_importers.py` | License check stops non-open repos, HyperUI and Uiverse parsing, re-imports keep your edits |
| `test_mcp.py` | All 6 MCP tools, their descriptions, and a real stdio round trip (starts `python -m designlib mcp` like Claude does) |
| `test_semantic.py` | Vector sync (only changed text is re-embedded), meaning matches with no shared words, filters on meaning results, rank fusion, the gallery never waiting for the model, fallback to keywords on failure. Uses a fake embedder; the `slow` test uses the real model |

## 2. MCP Inspector (click through the tools in a browser)

The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is the official,
free, open-source (MIT) test client for MCP servers. It needs Node.js (you have it).
`npx` downloads it the first time.

### Interactive UI

```powershell
npx @modelcontextprotocol/inspector python -m uv --directory "D:\C Skills\design-library-mcp" run python -m designlib mcp
```

1. The terminal prints a URL like `http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=...`
   and usually opens it for you. Use that exact URL (the token protects the proxy).
2. The left panel is pre-filled: **Transport** `STDIO`, the command and arguments above.
   Click **Connect**. The status turns green and shows `design-library`.
3. Open the **Tools** tab and click **List Tools**. You should see 6 tools:
   `search_designs`, `get_design`, `list_tags`, `list_styles`, `get_style_guide`, `add_design`.
4. Click `search_designs`, type `pricing` in **query**, click **Run Tool**.
   The result lists entries with a `gallery_url` for each.
5. Copy an `id` from the result, open `get_design`, paste it, and run it: you get the full
   entry including code. With the gallery running, the `gallery_url` opens its live preview.
6. Try `list_styles`, then `get_style_guide` with `quiet-product`.
7. Stop with Ctrl+C in the terminal.

`add_design` really writes to your library, so test it with a URL you want to keep
(or delete the new JSON file in `library/entries/` afterwards and run `rebuild`).

### Command-line mode (no browser)

Useful for a quick check or a script:

```powershell
# list the tools
npx @modelcontextprotocol/inspector --cli python -m uv --directory "D:\C Skills\design-library-mcp" run python -m designlib mcp --method tools/list

# call one
npx @modelcontextprotocol/inspector --cli python -m uv --directory "D:\C Skills\design-library-mcp" run python -m designlib mcp --method tools/call --tool-name search_designs --tool-arg query=hero --tool-arg limit=2
```

### If it doesn't connect

- Run `python -m uv run python -m designlib mcp` on its own. It should sit silently
  (it is waiting for a client). Any error printed there is the real problem.
- Nothing may print to stdout in server code: stdout carries the MCP messages.
  Use `print(..., file=sys.stderr)` or `logging` for debug output.
- After changing server code, click **Disconnect** then **Connect** so the Inspector
  starts a fresh server process.

## 3. Manual gallery check

```powershell
python -m uv run python -m designlib serve
```

Open http://127.0.0.1:8000 and check:

- [ ] Press `/`: the search box gets focus. Type `toggl`: results update without a reload
      and the address bar changes.
- [ ] Click a type chip, then a tag chip: results narrow. Browser Back restores the previous view.
- [ ] Favorites only + Sort work; "Clear all filters" appears when nothing matches.
- [ ] Open a component: Desktop / Tablet / Mobile resize the live preview; Copy code works.
- [ ] Add reference: "Fetch details" fills empty fields; upload a PNG; save; it shows on the grid.
- [ ] Try saving code with license `link-only`: the form refuses with a clear message.
- [ ] Theme toggle switches light/dark and is remembered after reload.
- [ ] Turn off Wi-Fi and reload: everything (fonts, HTMX, Tailwind previews) still works,
      except hotlinked preview images from other sites.
