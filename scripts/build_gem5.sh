#!/usr/bin/env bash
# build gem5.opt for one isa (default riscv). run inside wsl.
#   scripts/build_gem5.sh [ISA] [extra scons args]
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$here/env.sh"

isa="${1:-RISCV}"
shift || true

cd "$GEM5_ROOT"
scons "build/$isa/gem5.opt" -j"$(nproc)" "$@"
