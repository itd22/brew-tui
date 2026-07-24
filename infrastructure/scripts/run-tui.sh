#!/usr/bin/env bash
# infrastructure/scripts/run-tui.sh
#
# Tester command: "run BrewE2E and view tui"
#
# Execs into a running container as the "tester" user and runs ~/run-brewe2e.sh,
# forwarding all extra args (e.g. `install ripgrep`, `uninstall ripgrep`, or nothing
# for plain usage/help). Runs interactively (-it) so the tui/streamed brew output is
# visible in your terminal.
#
# Usage:
#   ./run-tui.sh <container> [brew-tui args...]
#
# Examples:
#   ./run-tui.sh brew-tui-dev
#   ./run-tui.sh brew-tui-dev install ripgrep
#   ./run-tui.sh brew-tui-dev uninstall ripgrep
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <container> [brew-tui args...]" >&2
    exit 1
fi

container="$1"
shift

docker exec -it --user tester "$container" /home/tester/run-brewe2e.sh "$@"
