#!/usr/bin/env python3
"""collect metrics from every results/<rob>/<bp>/<type>/<name>/stats.txt.

writes one csv row per run (default: results/summary.csv).

stats used (matched by suffix, so the board/core prefix does not matter):
    committed insts : commitStats0.numInsts
    cycles          : numCycles
    ipc             : commitStats0.ipc
    rob squashed    : commit.commitSquashedInsts
                      (squashed insts that reached the rob, skipped by commit)
    issued squashed : squashedInstsIssued (iq stat, sits on the core)
                      (squashed insts that were already issued to execute)
    mispredicts     : commit.branchMispredicts
    committed ctrl  : commitStats0.committedControl::IsControl
    resizer         : robResizer.restrictedFraction, .shrinks, .grows
                      (dynamic config only)

only the first stats dump in each file is read.
"""

import argparse
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# metric name -> stat name suffix
STATS = {
    "insts": "commitStats0.numInsts",
    "cycles": "numCycles",
    "ipc": "commitStats0.ipc",
    "sim_seconds": "simSeconds",
    "rob_squashed": "commit.commitSquashedInsts",
    "issued_squashed": "squashedInstsIssued",
    "mispredicts": "commit.branchMispredicts",
    "branches": "commitStats0.committedControl::IsControl",
    "restricted_fraction": "robResizer.restrictedFraction",
    "shrinks": "robResizer.shrinks",
    "grows": "robResizer.grows",
}


def read_stats(path: Path) -> dict:
    stats = {}
    seen_begin = False
    with open(path) as f:
        for line in f:
            if line.startswith("---------- Begin"):
                if seen_begin:
                    break
                seen_begin = True
                continue
            if line.startswith("---------- End"):
                break
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                stats[parts[0]] = float(parts[1])
            except ValueError:
                pass
    return stats


def pick(stats: dict, suffix: str):
    hits = [v for k, v in stats.items() if k == suffix or k.endswith("." + suffix)]
    if len(hits) > 1:
        raise ValueError(f"stat suffix '{suffix}' is ambiguous")
    return hits[0] if hits else None


def per_kilo(count, insts):
    if count is None or not insts:
        return None
    return 1000.0 * count / insts


def power_proxy(row: dict):
    return None


def collect(results: Path):
    rows = []
    for stats_path in sorted(results.glob("*/*/*/*/stats.txt")):
        rob, bp, wl_type, name = stats_path.parent.relative_to(results).parts
        stats = read_stats(stats_path)
        if not stats:
            print(f"warning: empty stats in {stats_path}", file=sys.stderr)
            continue
        row = {"rob": rob, "bp": bp, "workload_type": wl_type,
               "workload": name}
        for metric, suffix in STATS.items():
            row[metric] = pick(stats, suffix)
        row["rob_squashed_pki"] = per_kilo(row["rob_squashed"], row["insts"])
        row["issued_squashed_pki"] = per_kilo(row["issued_squashed"],
                                              row["insts"])
        row["mpki"] = per_kilo(row["mispredicts"], row["insts"])
        row["power_proxy"] = power_proxy(row)
        rows.append(row)
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--results", type=Path, default=REPO / "results")
    p.add_argument("-o", "--output", type=Path)
    args = p.parse_args()

    rows = collect(args.results)
    if not rows:
        sys.exit(f"no stats.txt files found under {args.results}")

    out = args.output or args.results / "summary.csv"
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
