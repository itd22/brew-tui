#!/usr/bin/env bash
# infrastructure/scripts/save-image.sh
#
# Tester command: "save current instance as image name, i.e. brew.<name>"
#
# Snapshots a running/stopped container's filesystem (including whatever the tester
# installed via Homebrew, plus ~/BrewTuiData and ~/BrewE2E) into a new image tagged
# brew.<name>.
#
# Usage:
#   ./save-image.sh <container> <name>
#
# Example:
#   ./save-image.sh brew-tui-dev ripgrep-installed
#   -> creates image "brew.ripgrep-installed"
set -euo pipefail

if [ $# -ne 2 ]; then
    echo "usage: $0 <container> <name>" >&2
    exit 1
fi

container="$1"
name="$2"
image="brew.${name}"

docker commit "$container" "$image"
echo "Saved container '$container' as image '$image'"
