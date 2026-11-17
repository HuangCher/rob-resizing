#!/usr/bin/env python3
"""Execute the ROB sizing experiment matrix.

Generates simulation configurations, executes gem5 workloads,
and records run metadata for reproducibility.

Usage and configuration are documented in the project README.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "configs"))
from window_configs import ROB_ENTRIES  # noqa: E402 (pure Python, no gem5 import)

ROB_CHOICES = tuple(ROB_ENTRIES)
BP_CHOICES = ("tage", "local")
TYPE_CHOICES = ("predictable", "unpredictable", "phased")
RESIZER_KEYS = (
    "window_insts", "min_window_branches", "shrink_rate", "grow_rate",
    "shrink_windows", "grow_windows",
)


def load_json(name: str) -> dict:
    """Load an experiments JSON file (fail early on malformed inputs)."""
    path = REPO / "experiments" / name
    with path.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return data


def _safe_binary_path(value: str) -> Path:
    path = (REPO / value).resolve()
    try:
        path.relative_to(REPO.resolve())
    except ValueError as error:
        raise ValueError(f"workload path escapes repository: {value}") from error
    return path


def _validate_resizer(resizer: dict) -> None:
    missing = [key for key in RESIZER_KEYS if resizer.get(key) is None]
    if missing:
        raise ValueError(
            "dynamic runs require non-null settings in experiments/resizer.json: "
            + ", ".join(missing)
            + "; ask Cher/Newman to finish tuning or select static ROBs"
        )
    for name in ("window_insts", "min_window_branches", "shrink_windows", "grow_windows"):
        if not isinstance(resizer[name], int) or isinstance(resizer[name], bool) or resizer[name] < 1:
            raise ValueError(f"resizer.{name} must be a positive integer")
    for name in ("shrink_rate", "grow_rate"):
        if not isinstance(resizer[name], (int, float)) or not 0 <= resizer[name] <= 1:
            raise ValueError(f"resizer.{name} must be in [0, 1]")
    if resizer["grow_rate"] > resizer["shrink_rate"]:
        raise ValueError("resizer.grow_rate cannot exceed shrink_rate")


def build_runs(args, baseline: dict, resizer: dict, workloads: dict) -> list[tuple[Path, list[str]]]:
    """Return (outdir, argv) for all selected jobs, in a stable order.

    Expected Newman run_o3.py flags: --rob-config, --bp, --binary,
    --binary-arg (repeatable), --clock, --max-insts, and dynamic flags.
    """
    if baseline.get("isa", "riscv").lower() != "riscv":
        raise ValueError("this workload suite is compiled for RISC-V only")
    max_insts = baseline.get("max_insts", 0)
    if not isinstance(max_insts, int) or max_insts < 0:
        raise ValueError("baseline.max_insts must be a nonnegative integer")
    if "dynamic" in args.rob_configs:
        _validate_resizer(resizer)

    jobs = []
    seen = set()
    for rob in args.rob_configs:
        for bp in args.predictors:
            for kind in args.types:
                entries = workloads.get(kind)
                if not isinstance(entries, list) or not entries:
                    raise ValueError(f"workloads.json: '{kind}' must be a nonempty list")
                for entry in entries:
                    if not isinstance(entry, dict):
                        raise ValueError(f"workloads.{kind}: expected object entries")
                    name, binary, argv = entry.get("name"), entry.get("binary"), entry.get("args", [])
                    if not isinstance(name, str) or not name or name in (".", "..") or "/" in name or "\\" in name:
                        raise ValueError(f"workloads.{kind}: unsafe workload name {name!r}")
                    if not isinstance(binary, str) or not isinstance(argv, list) or not all(isinstance(a, str) for a in argv):
                        raise ValueError(f"workloads.{kind}.{name}: binary must be a path, args a string list")
                    executable = _safe_binary_path(binary)
                    outdir = args.results.resolve() / rob / bp / kind / name
                    if outdir in seen:
                        raise ValueError(f"duplicate output directory: {outdir}")
                    seen.add(outdir)
                    cmd = [
                        str(args.gem5_binary.resolve()), f"--outdir={outdir}",
                        str(args.config.resolve()),
                        "--rob-config", rob, "--bp", bp, "--binary", str(executable),
                        "--max-insts", str(max_insts),
                    ]
                    if baseline.get("clock") is not None:
                        cmd += ["--clock", str(baseline["clock"])]
                    for argument in argv:
                        cmd += ["--binary-arg", argument]
                    if rob == "dynamic":
                        for key in RESIZER_KEYS:
                            cmd += ["--" + key.replace("_", "-"), str(resizer[key])]
                    jobs.append((outdir, cmd))
    return jobs


@lru_cache(maxsize=64)
def _sha256(path_name: str, size: int, mtime_ns: int) -> str:
    digest = hashlib.sha256()
    with Path(path_name).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _file_digest(path: Path) -> str | None:
    if not path.is_file():
        return None
    stat = path.stat()
    return _sha256(str(path.resolve()), stat.st_size, stat.st_mtime_ns)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _git_rev(path: Path) -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def _run_identity(cmd: list[str]) -> dict:
    # Include exact executable content, patch, and launcher code to prevent
    # accidentally treating stale output as valid when implementation changes.
    config = Path(cmd[2])
    binary = Path(cmd[cmd.index("--binary") + 1])
    gem5 = Path(cmd[0])
    return {
        "gem5_sha256": _file_digest(gem5),
        "workload_sha256": _file_digest(binary),
        "config_sha256": _file_digest(config),
        "patch_sha256": _file_digest(REPO / "gem5-patch" / "rob-resizing.patch"),
        "window_configs_sha256": _file_digest(REPO / "configs" / "window_configs.py"),
    }


def run_one(outdir: Path, cmd: list[str], gem5_root: Path | None = None,
            rerun: bool = False, timeout_seconds: float | None = None) -> str:
    """Execute one job, preserving its exact inputs and outcome in run.json.

    Returns 'skipped', 'success', 'failed', or 'timeout'.
    """
    gem5_root = (gem5_root or Path(os.environ.get("GEM5_ROOT", Path.home() / "gem5"))).resolve()
    identity = _run_identity(cmd)
    for path in (Path(cmd[0]), Path(cmd[2]), Path(cmd[cmd.index("--binary") + 1])):
        if not path.is_file():
            raise FileNotFoundError(f"required simulator/config/benchmark file missing: {path}")
    if not gem5_root.is_dir():
        raise FileNotFoundError(f"gem5 root does not exist: {gem5_root}")

    record_path = outdir / "run.json"
    if not rerun and record_path.is_file() and (outdir / "stats.txt").is_file():
        try:
            old = json.loads(record_path.read_text(encoding="utf-8"))
            if (old.get("status") == "success" and old.get("command") == cmd and old.get("identity") == identity and old.get("gem5_root") == str(gem5_root)):
                return "skipped"
        except (OSError, ValueError, TypeError):
            pass

    outdir.mkdir(parents=True, exist_ok=True)
    # gem5 may leave stale stats from a previous job on failure; remove them.
    (outdir / "stats.txt").unlink(missing_ok=True)
    (outdir / "simout").unlink(missing_ok=True)
    (outdir / "program.out").unlink(missing_ok=True)
    record = {
        "schema_version": 1,
        "status": "running",
        "command": cmd,
        "command_shell": shlex.join(cmd),
        "gem5_root": str(gem5_root),
        "identity": identity,
        "repo_commit": _git_rev(REPO),
        "gem5_commit": _git_rev(gem5_root),
        "host": platform.node(),
        "python": platform.python_version(),
        "started_utc": _utc_now(),
    }
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    start = time.monotonic()
    log_path = outdir / "simulator.log"
    with log_path.open("wb") as log:
        try:
            result = subprocess.run(cmd, cwd=gem5_root, stdout=log,
                                    stderr=subprocess.STDOUT, check=False,
                                    timeout=timeout_seconds)
            record["returncode"] = result.returncode
            record["status"] = ("success" if result.returncode == 0 and
                                ((outdir / "stats.txt").is_file() and (outdir / "stats.txt").stat().st_size > 0) else "failed")
        except subprocess.TimeoutExpired:
            log.write(f"\nlauncher: exceeded {timeout_seconds} seconds\n".encode())
            record["returncode"] = None
            record["status"] = "timeout"
        except OSError as error:
            log.write(f"launcher error: {error}\n".encode())
            record["returncode"] = None
            record["status"] = "failed"
    record["finished_utc"] = _utc_now()
    record["wall_seconds"] = round(time.monotonic() - start, 3)
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record["status"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rob-configs", nargs="+", choices=ROB_CHOICES, default=list(ROB_CHOICES))
    parser.add_argument("--predictors", nargs="+", choices=BP_CHOICES, default=list(BP_CHOICES))
    parser.add_argument("--types", nargs="+", choices=TYPE_CHOICES, default=list(TYPE_CHOICES))
    parser.add_argument("--results", type=Path, default=REPO / "results")
    parser.add_argument("--gem5-root", type=Path, default=Path(os.environ.get("GEM5_ROOT", Path.home() / "gem5")))
    parser.add_argument("--gem5-binary", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=REPO / "configs" / "run_o3.py")
    parser.add_argument("--dry-run", action="store_true", help="print commands without running or requiring binaries")
    parser.add_argument("--rerun", action="store_true", help="overwrite successful prior runs")
    parser.add_argument("--keep-going", action="store_true", help="continue even if one simulation fails")
    parser.add_argument("--limit", type=int, default=0, help="run only first N selected jobs (0 = all)")
    parser.add_argument("--timeout-seconds", type=float, default=0,
                        help="per-simulation wall-clock timeout (0 = unlimited)")
    args = parser.parse_args()
    if args.limit < 0:
        parser.error("--limit must be nonnegative")
    if args.timeout_seconds < 0:
        parser.error("--timeout-seconds must be nonnegative")
    args.gem5_binary = args.gem5_binary or args.gem5_root / "build" / "RISCV" / "gem5.opt"
    try:
        jobs = build_runs(args, load_json("baseline.json"), load_json("resizer.json"), load_json("workloads.json"))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    if args.limit:
        jobs = jobs[:args.limit]
    print(f"selected {len(jobs)} runs (ROB × branch predictor × workload)", flush=True)
    if args.dry_run:
        for outdir, cmd in jobs:
            print(f"\n# {outdir.relative_to(args.results.resolve())}\n{shlex.join(cmd)}")
        return 0
    failures = 0
    for index, (outdir, cmd) in enumerate(jobs, 1):
        print(f"[{index}/{len(jobs)}] {outdir.relative_to(args.results.resolve())}", flush=True)
        try:
            outcome = run_one(outdir, cmd, gem5_root=args.gem5_root,
                              rerun=args.rerun,
                              timeout_seconds=args.timeout_seconds or None)
        except (OSError, ValueError) as error:
            print(f"ERROR: {error}", file=sys.stderr)
            outcome = "failed"
        print(f"  {outcome}", flush=True)
        if outcome in ("failed", "timeout"):
            failures += 1
            if not args.keep_going:
                print(f"inspect {outdir / 'simulator.log'} and run.json", file=sys.stderr)
                break
    print(f"completed: {len(jobs)} selected, {failures} failure(s)", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
