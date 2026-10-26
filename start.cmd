@echo off
rem Double-click this file (or run `start.cmd`) to start the Design Library gallery.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First run: creating .venv and installing dependencies...
  python -m uv sync
)
".venv\Scripts\python.exe" -m designlib serve --open
