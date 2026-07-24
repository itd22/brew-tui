#!/bin/bash
# create venv and run as package
uv sync --python ../brew_env
PYTHONPATH=src uv run --python ../brew_env  python -m brew_tui.tui
