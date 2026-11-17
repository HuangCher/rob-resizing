#!/usr/bin/env python3
"""run the rob config x branch predictor x workload matrix in gem5.

owner: jacob. run inside wsl after `source scripts/env.sh`.

agreed layout: results/<rob>/<bp>/<workload_type>/<workload_name>/
inputs: experiments/baseline.json, resizer.json, workloads.json
gem5 entry point: configs/run_o3.py (see its --help for the flags)
"""

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "configs"))


def load_json(name):
    """load experiments/<name>."""
    raise NotImplementedError("todo(jacob)")


def build_runs(args, baseline, resizer, workloads):
    """return a list of (outdir, gem5 command) pairs for the selected runs."""
    raise NotImplementedError("todo(jacob)")


def run_one(outdir, cmd):
    """run one simulation and record what was run."""
    raise NotImplementedError("todo(jacob)")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.parse_args()
    raise NotImplementedError("todo(jacob)")


if __name__ == "__main__":
    main()
