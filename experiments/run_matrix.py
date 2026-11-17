#!/usr/bin/env python3
"""run the rob config x branch predictor x workload matrix in gem5.

run inside wsl with the gem5 env set up (source scripts/env.sh first).

results go to results/<rob>/<bp>/<workload_type>/<workload_name>/ and
contain stats.txt, config.ini, run.log and cmd.txt. finished runs (a
non-empty stats.txt) are skipped unless --force is given.

examples:
    python3 experiments/run_matrix.py --dry-run
    python3 experiments/run_matrix.py --rob small large --bp tage -j 4
"""

import argparse
import itertools
import json
import os
import shlex
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "configs"))

from window_configs import PREDICTORS, ROB_ENTRIES  # noqa: E402

RESIZER_KEYS = {
    "window_insts": "--window-insts",
    "min_window_branches": "--min-window-branches",
    "shrink_rate": "--shrink-rate",
    "grow_rate": "--grow-rate",
    "shrink_windows": "--shrink-windows",
    "grow_windows": "--grow-windows",
}


def load_json(name):
    with open(REPO / "experiments" / name) as f:
        data = json.load(f)
    data.pop("_note", None)
    return data


def build_runs(args, baseline, resizer, workloads):
    runs = []
    wl_types = args.workload_type or sorted(workloads)
    for rob, bp, wl_type in itertools.product(args.rob, args.bp, wl_types):
        for wl in workloads.get(wl_type, []):
            if args.workload and wl["name"] not in args.workload:
                continue
            outdir = REPO / "results" / rob / bp / wl_type / wl["name"]
            cmd = [
                str(args.gem5),
                f"--outdir={outdir}",
                str(REPO / "configs" / "run_o3.py"),
                "--rob", rob,
                "--bp", bp,
                "--isa", baseline["isa"],
                "--clock", baseline["clock"],
                "--binary", str(REPO / wl["binary"]),
            ]
            if baseline.get("max_insts"):
                cmd += ["--max-insts", str(baseline["max_insts"])]
            if baseline.get("disable_rvv"):
                cmd.append("--disable-rvv")
            if rob == "dynamic":
                for key, flag in RESIZER_KEYS.items():
                    cmd += [flag, str(resizer[key])]
            if wl.get("args"):
                cmd += ["--"] + [str(a) for a in wl["args"]]
            runs.append((outdir, cmd))
    return runs


def run_one(outdir: Path, cmd, force: bool, cwd: Path):
    stats = outdir / "stats.txt"
    if stats.exists() and stats.stat().st_size > 0 and not force:
        return f"skip   {outdir.relative_to(REPO)}"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "cmd.txt").write_text(shlex.join(cmd) + "\n")
    with open(outdir / "run.log", "w") as log:
        rc = subprocess.call(cmd, stdout=log, stderr=subprocess.STDOUT,
                             cwd=cwd)
    status = "ok    " if rc == 0 else f"FAIL {rc}"
    return f"{status} {outdir.relative_to(REPO)}"


def main():
    p =argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--gem5-root", type=Path,
                   default=Path(os.environ.get("GEM5_ROOT",
                                               Path.home() / "gem5")))
    p.add_argument("--gem5", type=Path,
                   help="gem5 binary (default: <gem5-root>/build/"
                        "<ISA>/gem5.opt)")
    p.add_argument("--rob", nargs="+", default=list(ROB_ENTRIES),
                   choices=list(ROB_ENTRIES))
    p.add_argument("--bp", nargs="+", default=list(PREDICTORS),
                   choices=list(PREDICTORS))
    p.add_argument("--workload-type", nargs="+")
    p.add_argument("--workload", nargs="+", help="filter by workload name")
    p.add_argument("-j", "--jobs", type=int, default=1)
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    baseline = load_json("baseline.json")
    resizer = load_json("resizer.json")
    workloads = load_json("workloads.json")

    if baseline.get("clock") is None:
        sys.exit("experiments/baseline.json: clock is not set yet")
    if args.gem5 is None:
        args.gem5 = (args.gem5_root / "build" / baseline["isa"].upper()
                     / "gem5.opt")

    if "dynamic" in args.rob:
        unset = [k for k in RESIZER_KEYS if resizer.get(k) is None]
        if unset:
            print("note: skipping dynamic runs, resizer.json has unset "
                  f"keys: {', '.join(unset)}", file=sys.stderr)
            args.rob = [r for r in args.rob if r != "dynamic"]

    runs = build_runs(args, baseline, resizer, workloads)
    if not runs:
        sys.exit("no runs selected (is experiments/workloads.json empty?)")

    if args.dry_run:
        for outdir, cmd in runs:
            print(shlex.join(cmd))
        print(f"{len(runs)} runs", file=sys.stderr)
        return

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        jobs = [pool.submit(run_one, outdir, cmd, args.force, args.gem5_root)
                for outdir, cmd in runs]
        for job in jobs:
            print(job.result(), flush=True)


if __name__ == "__main__":
    main()
