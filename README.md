# design-library-mcp

A local, free, open-source design-reference library: a web gallery you browse and an
MCP server Claude queries, so UI work starts from references you picked on purpose.

Full setup instructions arrive in milestone M7. For now:

```powershell
python -m uv sync                              # create .venv and install dependencies
python -m uv run pytest                        # run the tests
python -m uv run python -m designlib serve     # gallery at http://127.0.0.1:8000
python -m uv run python -m designlib add <url> --type screen --tags hero,saas
python -m uv run python -m designlib search pricing
```

Third-party files stored in the project (`src/designlib/web/static/vendor/`), each with its license:
htmx 2.0.4 (0BSD), Tailwind CSS browser build 4.1.11 (MIT), highlight.js 11.10.0 (BSD-3),
Familjen Grotesk font (SIL OFL 1.1).
