#!/usr/bin/env python3
"""Extract gem5 metrics from results/<rob>/<bp>/<type>/<name>/stats.txt.

Important: stock gem5 'squashedInstsIssued' is NOT a count of issued
wrong-path instructions. Do not substitute it for rob.squashedIssuedInsts.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIELDS = (
    "rob", "predictor", "workload_type", "workload", "status", "results_dir",
    "sim_ticks", "sim_seconds", "num_cycles", "committed_insts", "ipc", "cpi",
    "branch_mispredicts", "committed_branches", "branch_mispredict_rate",
    "branch_mispredict_stat", "committed_branches_stat",
    "pred_cond_incorrect", "pred_cond_predicted", "pred_cond_error_rate",
    "rob_squashed_insts", "rob_squashed_issued_insts",
    "rob_squashed_executed_insts", "issued_squashes_per_1k_committed",
    "resizer_windows", "resizer_quiet_windows", "resizer_shrinks", "resizer_grows",
    "resizer_insts_full", "resizer_insts_restricted", "resizer_restricted_fraction",
    "program_checksum", "wall_seconds", "gem5_sha256", "workload_sha256",
)
NUM_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
CHECKSUM_RE = re.compile(r"\bchecksum=([0-9a-fA-F]+)\b")


def _number(value: str):
    if value.lower() in ("nan", "-nan", "+nan", "inf", "-inf", "+inf"):
        return None
    if not NUM_RE.fullmatch(value):
        return None
    try:
        return int(value) if re.fullmatch(r"[+-]?\d+", value) else float(value)
    except ValueError:
        return None


def read_stats(path: Path) -> dict:
    """Read gem5 stats, keeping the last completed statistics block.

    gem5 can dump stats multiple times. A cut-off/truncated final block is
    ignored if a prior completed block exists.
    """
    current, last_complete = {}, None
    inside_block = False
    saw_block = False
    with path.open("r", encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if "Begin Simulation Statistics" in line:
                current = {}
                inside_block = True
                saw_block = True
                continue
            if "End Simulation Statistics" in line:
                if inside_block:
                    last_complete = current
                inside_block = False
                continue
            parts = line.split("#", 1)[0].split()
            if len(parts) < 2 or (saw_block and not inside_block):
                continue
            value = _number(parts[1])
            if value is not None:
                current[parts[0]] = value
    return last_complete if last_complete is not None else current


def _get(stats: dict, *suffixes: str):
    """Select an exact key or dotted-stat suffix, recording its real name."""
    for suffix in suffixes:
        if suffix in stats:
            return stats[suffix], suffix
        matches = sorted((k for k in stats if k.endswith("." + suffix)))
        if len(matches) == 1:
            return stats[matches[0]], matches[0]
        if len(matches) > 1:
            raise ValueError(f"multiple CPU stats matched '.{suffix}': {matches}")
    return None, ""


def _safe_div(numerator, denominator):
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _metric(stats: dict, *suffixes: str):
    return _get(stats, *suffixes)[0]


def _checksum(run_dir: Path):
    # Some gem5 SE configurations redirect guest stdout to simout.
    for name in ("simulator.log", "simout", "program.out", "stdout.txt"):
        log = run_dir / name
        if not log.is_file():
            continue
        with log.open("rb") as stream:
            stream.seek(0, 2)
            stream.seek(max(0, stream.tell() - 65536))
            tail = stream.read().decode("utf-8", errors="replace")
        matches = CHECKSUM_RE.findall(tail)
        if matches:
            return matches[-1].lower()
    return None


def _row(stats: dict, run_dir: Path, results: Path, manifest: dict) -> dict:
    rel = run_dir.relative_to(results).parts
    rob, bp, kind, workload = rel
    cycles = _metric(stats, "numCycles")
    committed = _metric(stats, "commitStats0.numInsts", "commitStats.numInsts", "committedInsts", "numInsts")
    ipc = _metric(stats, "ipc", "ipc::total")
    if ipc is None:
        ipc = _safe_div(committed, cycles)
    cpi = _metric(stats, "cpi", "cpi::total")
    if cpi is None:
        cpi = _safe_div(1.0, ipc)
    ticks = _metric(stats, "simTicks", "sim_ticks")
    if ticks is None or (ipc is None and committed is None):
        raise ValueError("stats.txt lacks simTicks or useful CPU execution metrics")
    sim_freq = _metric(stats, "simFreq")
    mispredicts, mispredict_key = _get(
        stats, "commit.branchMispredicts", "robResizer.mispredicts", "branchPred.condIncorrect")
    branches, branches_key = _get(
        stats, "robResizer.branches", "commitStats0.committedBranchInsts",
        "commitStats0.committedControlInsts", "commitStats0.numBranches")
    pred_cond_incorrect = _metric(stats, "branchPred.condIncorrect")
    pred_cond_predicted = _metric(stats, "branchPred.condPredicted")
    squashed = _metric(stats, "rob.squashedInsts")
    issued = _metric(stats, "rob.squashedIssuedInsts")
    executed = _metric(stats, "rob.squashedExecutedInsts")
    full = _metric(stats, "robResizer.instsFull")
    restricted = _metric(stats, "robResizer.instsRestricted")
    restricted_fraction = _metric(stats, "robResizer.restrictedFraction")
    if restricted_fraction is None and full is not None and restricted is not None:
        restricted_fraction = _safe_div(restricted, full + restricted)
    identity = manifest.get("identity", {})
    return {
        "rob": rob, "predictor": bp, "workload_type": kind,
        "workload": workload, "status": manifest.get("status", "unrecorded"),
        "results_dir": str(run_dir),
        "sim_ticks": ticks, "sim_seconds": _safe_div(ticks, sim_freq),
        "num_cycles": cycles, "committed_insts": committed,
        "ipc": ipc, "cpi": cpi,
        "branch_mispredicts": mispredicts, "committed_branches": branches,
        "branch_mispredict_rate": _safe_div(mispredicts, branches) if not mispredict_key.endswith("branchPred.condIncorrect") else None,
        "pred_cond_incorrect": pred_cond_incorrect,
        "pred_cond_predicted": pred_cond_predicted,
        "pred_cond_error_rate": _safe_div(pred_cond_incorrect, pred_cond_predicted),
        "branch_mispredict_stat": mispredict_key,
        "committed_branches_stat": branches_key,
        "rob_squashed_insts": squashed,
        "rob_squashed_issued_insts": issued,
        "rob_squashed_executed_insts": executed,
        "issued_squashes_per_1k_committed": (1000 * issued / committed if
            issued is not None and committed is not None and committed > 0 else None),
        "resizer_windows": _metric(stats, "robResizer.windows"),
        "resizer_quiet_windows": _metric(stats, "robResizer.quietWindows"),
        "resizer_shrinks": _metric(stats, "robResizer.shrinks"),
        "resizer_grows": _metric(stats, "robResizer.grows"),
        "resizer_insts_full": full, "resizer_insts_restricted": restricted,
        "resizer_restricted_fraction": restricted_fraction,
        "program_checksum": _checksum(run_dir),
        "wall_seconds": manifest.get("wall_seconds"),
        "gem5_sha256": identity.get("gem5_sha256"),
        "workload_sha256": identity.get("workload_sha256"),
    }


def collect(results: Path) -> list[dict]:
    """Return one row for each successfully completed 4-level run directory."""
    rows = []
    if not results.is_dir():
        return rows
    for path in sorted(results.rglob("stats.txt")):
        run_dir = path.parent
        if len(run_dir.relative_to(results).parts) != 4:
            continue
        manifest_path = run_dir / "run.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
            if manifest.get("status", "success") != "success":
                print(f"WARNING: ignoring failed run {run_dir}", file=sys.stderr)
                continue
            rows.append(_row(read_stats(path), run_dir, results, manifest))
        except (OSError, ValueError, TypeError, KeyError) as error:
            print(f"WARNING: ignoring {run_dir}: {error}", file=sys.stderr)
    # Equal inputs must produce equal checksums across all configurations.
    # A mismatch invalidates performance comparisons.
    checksums = {}
    for row in rows:
        key = (row["workload_type"], row["workload"])
        checksum = row["program_checksum"]
        if checksum is not None:
            checksums.setdefault(key, set()).add(checksum)
    for key, values in checksums.items():
        if len(values) > 1:
            print(f"WARNING: inconsistent checksums for {key}: {sorted(values)}", file=sys.stderr)
    return rows


def energy_proxy(row: dict):
    """Reserved for Newman's validated power-proxy model; not guessed here."""
    raise NotImplementedError("todo(newman): define and justify an energy proxy")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results", type=Path, default=REPO / "results")
    parser.add_argument("--csv", type=Path, default=None)
    args = parser.parse_args()
    results = args.results.resolve()
    output = args.csv or results / "summary.csv"
    rows = collect(results)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {output}")
    if not rows:
        print("WARNING: no completed gem5 runs found", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
