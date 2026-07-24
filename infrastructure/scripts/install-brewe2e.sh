#!/usr/bin/env bash
# infrastructure/scripts/install-brewe2e.sh
#
# Tester command: "external install BrewE2E by removing current ~/tester and copy new"
#
# Replaces the BrewE2E implementation inside a running container: deletes the
# container's current ~tester/BrewE2E and copies in a new one from the host.
#
# Usage:
#   ./install-brewe2e.sh <container> <path-to-new-BrewE2E-source-dir>
#
# Example:
#   ./install-brewe2e.sh brew-tui-dev ../my-updated-brew_tui-src
#   -> that directory's contents replace ~tester/BrewE2E/src/brew_tui in the container
set -euo pipefail

if [ $# -ne 2 ]; then
    echo "usage: $0 <container> <path-to-new-BrewE2E-source-dir>" >&2
    exit 1
fi

container="$1"
new_src="$2"

if [ ! -d "$new_src" ]; then
    echo "error: '$new_src' is not a directory" >&2
    exit 1
fi

echo "Removing current ~tester/BrewE2E in '$container'..."
docker exec --user tester "$container" rm -rf /home/tester/BrewE2E

echo "Recreating ~tester/BrewE2E and copying in new sources from '$new_src'..."
docker exec --user tester "$container" mkdir -p /home/tester/BrewE2E/src
docker cp "$new_src/." "$container:/home/tester/BrewE2E/src/"

docker exec --user tester "$container" chown -R tester:tester /home/tester/BrewE2E
echo "Installed new BrewE2E into '$container':/home/tester/BrewE2E"
