# design-library-mcp

A local, free, open-source design-reference library: a web gallery you browse and an
MCP server Claude queries, so UI work starts from references you picked on purpose.

Full setup instructions arrive in milestone M7. For now:

```powershell
python -m uv sync          # create .venv and install dependencies
python -m uv run pytest    # run the tests
python -m uv run python -m designlib rebuild
```
