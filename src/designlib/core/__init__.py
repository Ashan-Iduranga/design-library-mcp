"""Shared logic used by the CLI, the web gallery and the MCP server.

schema   - what an entry looks like (pydantic model + validation rules)
storage  - reading/writing entry JSON files (the source of truth)
index    - building the SQLite + FTS5 index from those files
search   - querying the index
"""
