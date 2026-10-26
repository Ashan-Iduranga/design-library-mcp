#!/usr/bin/env sh
# Start the Design Library gallery (Git Bash / macOS / Linux).
cd "$(dirname "$0")" || exit 1
[ -d .venv ] || python -m uv sync
if [ -x .venv/Scripts/python.exe ]; then PY=.venv/Scripts/python.exe; else PY=.venv/bin/python; fi
exec "$PY" -m designlib serve --open
