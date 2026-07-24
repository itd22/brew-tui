#!/usr/bin/env bash
# ~tester/install-homebrew.sh
#
# Installs real Homebrew (Linuxbrew) as the "tester" user. Safe to re-run: it's a no-op
# if brew is already on PATH.
set -euo pipefail

if command -v brew >/dev/null 2>&1; then
    echo "Homebrew already installed at $(command -v brew)"
    brew --version
    exit 0
fi

echo "Installing Homebrew (this shells out to the official install script)..."
NONINTERACTIVE=1 /bin/bash -c \
    "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

BREW_BIN="/home/linuxbrew/.linuxbrew/bin/brew"
if [ -x "$BREW_BIN" ]; then
    echo "eval \"\$($BREW_BIN shellenv)\"" >> "$HOME/.bashrc"
    eval "$("$BREW_BIN" shellenv)"
    brew --version
else
    echo "Homebrew install script finished but $BREW_BIN was not found." >&2
    exit 1
fi
