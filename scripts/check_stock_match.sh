#!/usr/bin/env bash
# validation: a static rob config must give identical stats on the modified
# gem5 and on the stock binary (~/gem5-stock/gem5.opt, saved before the
# rob resizing changes). ignore host-side stats and the new rob.squashed*
# stats, which only the modified binary has.
# todo(newman): implement.
set -euo pipefail

echo "not implemented" >&2
exit 1
