#!/usr/bin/env python3
"""collect metrics from results/<rob>/<bp>/<type>/<name>/stats.txt.

owner: jacob (parsing), newman (power proxy).

stats added by the gem5 changes (prefix is the cpu, e.g.
board.processor.cores.core):
    rob.squashedIssuedInsts    squashed after issue (power proxy input)
    rob.squashedInsts          every inst squashed out of the rob
    rob.squashedExecutedInsts  squashed after it finished executing
    robResizer.*               fsm stats, dynamic config only

note: stock gem5's squashedInstsIssued is not wrong-path work. it counts
insts the iq skips because they are already squashed.
"""

import argparse
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def read_stats(path: Path) -> dict:
    """parse a stats.txt dump into {stat name: value}."""
    raise NotImplementedError("todo(jacob)")


def collect(results: Path) -> list:
    """return one row of metrics per run."""
    raise NotImplementedError("todo(jacob)")


def energy_proxy(row: dict):
    """power proxy for one run."""
    raise NotImplementedError("todo(newman)")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--results", type=Path, default=REPO / "results")
    p.parse_args()
    raise NotImplementedError("todo(jacob)")


if __name__ == "__main__":
    main()
