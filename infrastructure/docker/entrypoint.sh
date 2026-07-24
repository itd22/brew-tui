#!/usr/bin/env bash
# infrastructure/docker/entrypoint.sh
set -euo pipefail

mkdir -p "$(dirname "${HOMEBREW_DB_PATH}")"

if [ -t 1 ] && [ "${1:-}" = "bash" ]; then
    cat <<'BANNER'
brew-tui test container
------------------------
  ~/BrewE2E        BrewE2E / brew_tui implementation (PYTHONPATH already set)
  ~/BrewTuiData    brew-tui's sqlite package DB (HOMEBREW_DB_PATH)

  ./install-homebrew.sh          install real Homebrew (idempotent)
  ./run-brewe2e.sh <args...>     run BrewE2E / brew-tui, e.g.:
                                    ./run-brewe2e.sh install ripgrep
                                    ./run-brewe2e.sh list

From the HOST, see infrastructure/scripts/ for:
  save-image.sh          docker commit this container as brew.<name>
  install-brewe2e.sh      swap in a new ~/BrewE2E from the host
  run-tui.sh              docker exec in and run BrewE2E / view the tui
BANNER
fi

exec "$@"
