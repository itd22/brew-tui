#!/usr/bin/env bash
# ~tester/run-brewe2e.sh
#
# Runs BrewE2E's brew-tui entry point against ~/BrewE2E, storing/reading its DB at
# ~/BrewTuiData/brew.db. Forwards all args, e.g.:
#   ./run-brewe2e.sh install ripgrep
#   ./run-brewe2e.sh uninstall ripgrep
#   ./run-brewe2e.sh            (prints tui usage)
set -euo pipefail

export PYTHONPATH="${BREW_E2E_HOME:-$HOME/BrewE2E}/src:${PYTHONPATH:-}"
export HOMEBREW_DB_PATH="${HOMEBREW_DB_PATH:-$HOME/BrewTuiData/brew.db}"
mkdir -p "$(dirname "$HOMEBREW_DB_PATH")"

if [ -x "/home/linuxbrew/.linuxbrew/bin/brew" ]; then
    eval "$(/home/linuxbrew/.linuxbrew/bin/brew shellenv)"
fi

exec python3 -m brew_tui "$@"
