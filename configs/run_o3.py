"""gem5 se-mode run script for the rob resizing sweep.

owner: newman (baseline config), cher (rob resizer hookup).

run from the gem5 root:
    build/RISCV/gem5.opt --outdir=<dir> <repo>/configs/run_o3.py [flags]

static configs must not create a RobResizer, so this script also runs on
an unmodified gem5 binary for validation.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import m5.objects  # noqa: E402


def parse_args():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # todo(newman): rob config, predictor, clock, binary, etc.

    g = p.add_argument_group("rob resizer (dynamic config only)")
    g.add_argument("--window-insts", type=int)
    g.add_argument("--min-window-branches", type=int, default=1)
    g.add_argument("--shrink-rate", type=float)
    g.add_argument("--grow-rate", type=float)
    g.add_argument("--shrink-windows", type=int)
    g.add_argument("--grow-windows", type=int)
    return p.parse_args()


def make_rob_resizer(args, restricted_entries: int):
    """build the RobResizer for the dynamic config.

    attach with cpu.robResizer = make_rob_resizer(...). the cpu's
    numROBEntries is the full size; restricted_entries is the shrunk size.
    """
    return m5.objects.RobResizer(
        restrictedROBEntries=restricted_entries,
        windowInsts=args.window_insts,
        minWindowBranches=args.min_window_branches,
        shrinkMispredictRate=args.shrink_rate,
        growMispredictRate=args.grow_rate,
        shrinkWindows=args.shrink_windows,
        growWindows=args.grow_windows,
    )


def make_branch_predictor(kind: str):
    """tage (high accuracy) or 2-bit local (low accuracy)."""
    raise NotImplementedError("todo(newman)")


def make_cpu(args):
    """o3 cpu with rob/iq/lsq/register sizes for the selected config."""
    raise NotImplementedError("todo(newman)")


def main():
    args = parse_args()
    # todo(newman): board, caches, memory, workload, simulator
    raise NotImplementedError("todo(newman)")


main()
