#!/usr/bin/env bash
# Build the canonical workloads/Makefile, then emit/check RISC-V disassembly.
# Usage: scripts/build_workloads.sh [riscv-linux-gcc] [riscv-linux-objdump]
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ $# -ge 1 ]]; then
    compiler="$1"
elif command -v riscv64-linux-gnu-gcc >/dev/null 2>&1; then
    compiler=riscv64-linux-gnu-gcc
else
    echo 'error: no RISC-V Linux cross-compiler; install gcc-riscv64-linux-gnu or pass its full path' >&2
    exit 1
fi
if [[ $# -ge 2 ]]; then
    objdump="$2"
else
    objdump="${compiler%gcc}objdump"
fi
if ! command -v "$compiler" >/dev/null 2>&1; then
    echo "error: compiler not found: $compiler" >&2
    exit 1
fi

# Do not independently set flags here; keep workloads/Makefile authoritative.
# Force rebuild: make otherwise considers stale native or differently flagged binaries up to date.
make -B -C "$repo/workloads" "CC=$compiler"

for name in predictable unpredictable phased; do
    bin="$repo/workloads/bin/$name"
    echo "built $bin"
    if command -v "$objdump" >/dev/null 2>&1; then
        disasm="$repo/workloads/bin/$name.disasm"
        "$objdump" -d "$bin" > "$disasm"
        # Check the benchmark kernel, never branches from static libc.
        if ! grep -Eq '<run_kernel([.]constprop[.][0-9]+)?>:' "$disasm"; then
            echo "ERROR: run_kernel symbol missing from $name disassembly" >&2
            exit 1
        fi
        if ! awk '/<run_kernel([.]constprop[.][0-9]+)?>:/{inside=1;next} inside && /^$/{exit} inside {print}' "$disasm" | \
            grep -Eq '(^|[[:space:]])(beq|bne|blt|bge|bltu|bgeu|beqz|bnez)([[:space:]]|$)'; then
            echo "ERROR: no conditional RISC-V branch observed in $name run_kernel" >&2
            exit 1
        fi
        echo "verified conditional branches in $name (details: $disasm)"
    else
        echo "WARNING: $objdump not found. Branch verification is still REQUIRED." >&2
    fi
done
