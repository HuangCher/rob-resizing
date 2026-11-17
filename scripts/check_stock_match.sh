#!/usr/bin/env bash
# check that a static rob config gives identical stats on the modified gem5
# and on the unmodified (stock) binary. host-side stats (time, memory,
# sim speed) are ignored.
#   scripts/check_stock_match.sh <binary> [rob config] [bp] [clock]
# STOCK_GEM5 defaults to ~/gem5-stock/gem5.opt (a copy of the build made
# before the rob resizing changes).
set -euo pipefail

repo="$(cd "$(dirname "$0")/.." && pwd)"
gem5="${GEM5_ROOT:-$HOME/gem5}"
stock="${STOCK_GEM5:-$HOME/gem5-stock/gem5.opt}"
modified="${MODIFIED_GEM5:-$gem5/build/RISCV/gem5.opt}"

binary="$(realpath "$1")"
rob="${2:-large}"
bp="${3:-tage}"
clock="${4:-3GHz}"
max_insts="${MAX_INSTS:-1000000}"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

run () {   # $1 = gem5 binary, $2 = outdir
    (cd "$gem5" && "$1" --outdir="$2" "$repo/configs/run_o3.py" \
        --rob "$rob" --bp "$bp" --clock "$clock" \
        --max-insts "$max_insts" --binary "$binary" ${EXTRA_ARGS:-}) \
        > "$2.log" 2>&1
}

run "$stock" "$work/stock"
run "$modified" "$work/modified"

for d in stock modified; do
    if [ ! -s "$work/$d/stats.txt" ]; then
        echo "FAILED: no stats from $d run"; tail -20 "$work/$d.log"; exit 1
    fi
done

# drop host-dependent lines before comparing
filter () { grep -v -E '^[^ ]*host[A-Z]' "$1"; }
filter "$work/stock/stats.txt" > "$work/a"
filter "$work/modified/stats.txt" > "$work/b"

if diff -q "$work/a" "$work/b" > /dev/null; then
    echo "match: $rob/$bp stats identical on stock and modified gem5"
else
    echo "MISMATCH: $rob/$bp"
    diff "$work/a" "$work/b" | head -40
    exit 1
fi
