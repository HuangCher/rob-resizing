"""gem5 se-mode run script for the rob resizing sweep.

usage (from the gem5 root, see scripts/run_one.sh):

    build/RISCV/gem5.opt --outdir=<dir> <repo>/configs/run_o3.py \
        --rob large --bp tage --clock 3GHz --binary <path> [-- args...]

the dynamic config also needs the resizer parameters:

    --rob dynamic --window-insts N --shrink-rate R --grow-rate R \
        --shrink-windows N --grow-windows N

static configs never touch RobResizer, so this script also runs on an
unmodified gem5 binary (used by scripts/check_stock_match.sh).
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from window_configs import (  # noqa: E402
    DYNAMIC_RESTRICTED_ROB,
    PREDICTORS,
    ROB_ENTRIES,
    window_sizes,
)

from gem5.components.boards.simple_board import SimpleBoard  # noqa: E402
from gem5.components.cachehierarchies.classic.private_l1_private_l2_cache_hierarchy import (  # noqa: E402,E501
    PrivateL1PrivateL2CacheHierarchy,
)
from gem5.components.memory import SingleChannelDDR3_1600  # noqa: E402
from gem5.components.processors.base_cpu_core import BaseCPUCore  # noqa: E402
from gem5.components.processors.base_cpu_processor import (  # noqa: E402
    BaseCPUProcessor,
)
from gem5.isas import ISA  # noqa: E402
from gem5.resources.resource import BinaryResource  # noqa: E402
from gem5.simulate.simulator import Simulator  # noqa: E402

import m5.objects  # noqa: E402

ISA_CPU = {
    "riscv": (ISA.RISCV, "RiscvO3CPU"),
    "x86": (ISA.X86, "X86O3CPU"),
    "arm": (ISA.ARM, "ArmO3CPU"),
}


def parse_args():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--rob", required=True, choices=sorted(ROB_ENTRIES))
    p.add_argument("--bp", required=True, choices=sorted(PREDICTORS))
    p.add_argument("--isa", default="riscv", choices=sorted(ISA_CPU))
    # baseline clock is not decided yet, so it is always passed explicitly
    p.add_argument("--clock", required=True, help="core clock, e.g. 3GHz")
    p.add_argument("--binary", required=True, help="static se-mode binary")
    p.add_argument("--max-insts", type=int, default=0,
                   help="stop after this many committed insts (0 = run "
                        "to completion)")
    p.add_argument("--disable-rvv", action="store_true",
                   help="turn off the riscv vector extension")

    g = p.add_argument_group("resizer (only used with --rob dynamic)")
    g.add_argument("--window-insts", type=int)
    g.add_argument("--min-window-branches", type=int, default=1)
    g.add_argument("--shrink-rate", type=float)
    g.add_argument("--grow-rate", type=float)
    g.add_argument("--shrink-windows", type=int)
    g.add_argument("--grow-windows", type=int)

    p.add_argument("binary_args", nargs=argparse.REMAINDER,
                   help="arguments for the binary, after --")
    args = p.parse_args()

    if args.binary_args and args.binary_args[0] == "--":
        args.binary_args = args.binary_args[1:]

    if args.rob == "dynamic":
        missing = [
            name for name in ("window_insts", "shrink_rate", "grow_rate",
                              "shrink_windows", "grow_windows")
            if getattr(args, name) is None
        ]
        if missing:
            p.error("--rob dynamic needs: " + ", ".join(
                "--" + m.replace("_", "-") for m in missing))
    return args


def make_branch_predictor(kind: str):
    if kind == "tage":
        cond = m5.objects.TAGE()
    elif kind == "local":
        # localCtrBits defaults to 2, set it anyway so the intent is explicit
        cond = m5.objects.LocalBP(localCtrBits=2)
    else:
        raise ValueError(kind)
    return m5.objects.BranchPredictor(conditionalBranchPred=cond)


def make_cpu(args):
    isa, cpu_class = ISA_CPU[args.isa]
    cpu = getattr(m5.objects, cpu_class)()
    sizes = window_sizes(args.rob)

    cpu.numROBEntries = sizes["rob"]
    # stock o3 has a single iq unit; scale it like the rob
    for iq in cpu.instQueues:
        iq.numEntries = sizes["iq"]
    cpu.LQEntries = sizes["lq"]
    cpu.SQEntries = sizes["sq"]
    cpu.branchPred = make_branch_predictor(args.bp)

    if args.max_insts:
        cpu.max_insts_any_thread = args.max_insts

    if args.rob == "dynamic":
        cpu.robResizer = m5.objects.RobResizer(
            restrictedROBEntries=DYNAMIC_RESTRICTED_ROB,
            windowInsts=args.window_insts,
            minWindowBranches=args.min_window_branches,
            shrinkMispredictRate=args.shrink_rate,
            growMispredictRate=args.grow_rate,
            shrinkWindows=args.shrink_windows,
            growWindows=args.grow_windows,
        )
    return isa, cpu


def main():
    args = parse_args()
    isa, cpu = make_cpu(args)

    core = BaseCPUCore(core=cpu, isa=isa)
    if args.disable_rvv:
        for t in core.core.isa:
            t.enable_rvv = False
    processor = BaseCPUProcessor(cores=[core])

    # placeholder: baseline cache hierarchy and memory are not decided yet
    cache_hierarchy = PrivateL1PrivateL2CacheHierarchy(
        l1d_size="32KiB", l1i_size="32KiB", l2_size="512KiB"
    )
    memory = SingleChannelDDR3_1600(size="2GiB")

    board = SimpleBoard(
        clk_freq=args.clock,
        processor=processor,
        memory=memory,
        cache_hierarchy=cache_hierarchy,
    )
    board.set_se_binary_workload(
        BinaryResource(local_path=os.path.abspath(args.binary)),
        arguments=args.binary_args,
    )

    print(f"rob config: {args.rob} {window_sizes(args.rob)}, bp: {args.bp}")
    simulator = Simulator(board=board)
    simulator.run()
    print(f"exit: {simulator.get_last_exit_event_cause()}")


main()
