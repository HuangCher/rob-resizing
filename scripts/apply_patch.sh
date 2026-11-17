#!/usr/bin/env bash
# apply gem5-patch/rob-resizing.patch to a clean gem5 checkout.
#   scripts/apply_patch.sh [gem5 root]
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
gem5="${1:-${GEM5_ROOT:-$HOME/gem5}}"

cd "$gem5"
git apply --check "$repo/gem5-patch/rob-resizing.patch"
git apply "$repo/gem5-patch/rob-resizing.patch"
echo "applied to $gem5"
