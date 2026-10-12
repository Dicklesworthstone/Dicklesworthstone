#!/usr/bin/env bash
# Installed as ~/.local/bin/profile-stats-update.sh. Runs a snapshot of the
# versioned nightly script, because that script `git pull`s this repository
# and bash would otherwise keep reading a file the pull may have rewritten.
src="$HOME/projects/Dicklesworthstone/ops/profile-stats-update.sh"
dir="$HOME/.local/share/profile-stats"
mkdir -p "$dir" || exit 1
snapshot=$(mktemp "$dir/.wrapper.XXXXXX") || exit 1
trap 'rm -f "$snapshot"' EXIT
cp "$src" "$snapshot" || exit 1
/bin/bash "$snapshot" "$@"
