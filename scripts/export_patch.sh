#!/usr/bin/env bash
# snapshot the gem5 changes into gem5-patch/rob-resizing.patch so they are
# tracked in this repo. only src/cpu/o3 is exported; new (untracked) files
# are included as diffs against /dev/null.
#   scripts/export_patch.sh
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
gem5="${GEM5_ROOT:-$HOME/gem5}"
out="$repo/gem5-patch/rob-resizing.patch"
mkdir -p "$(dirname "$out")"

cd "$gem5"
{
    echo "# base: $(git rev-parse HEAD) ($(git describe --tags 2>/dev/null || echo unknown))"
    git diff -- src/cpu/o3
    # untracked new files, diffed against /dev/null
    git ls-files --others --exclude-standard -- src/cpu/o3 | while read -r f; do
        git diff --no-index -- /dev/null "$f" || true
    done
} > "$out"

echo "wrote $out"
