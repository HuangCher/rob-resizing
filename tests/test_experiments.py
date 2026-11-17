"""Local unit/smoke tests (no installed gem5/RISC-V compiler required).
Run: python3 -m unittest discover -s tests -v
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


runner = load_module("run_matrix", ROOT / "experiments" / "run_matrix.py")
collector = load_module("collect", ROOT / "analysis" / "collect.py")


class BenchExperimentTests(unittest.TestCase):
    def test_matrix(self):
        with tempfile.TemporaryDirectory() as temp:
            args = SimpleNamespace(
                rob_configs=list(runner.ROB_CHOICES), predictors=list(runner.BP_CHOICES),
                types=list(runner.TYPE_CHOICES), results=Path(temp),
                gem5_binary=Path(temp) / "gem5.opt", config=ROOT / "configs" / "run_o3.py",
            )
            baseline = runner.load_json("baseline.json")
            resizer = dict(runner.load_json("resizer.json"))
            resizer.update(shrink_rate=0.2, grow_rate=0.05, shrink_windows=2, grow_windows=2)
            workloads = runner.load_json("workloads.json")
            jobs = runner.build_runs(args, baseline, resizer, workloads)
            self.assertEqual(len(jobs), 30)
            self.assertEqual(len(set(str(path) for path, _ in jobs)), 30)
            dynamic = [cmd for _, cmd in jobs if cmd[cmd.index("--rob-config") + 1] == "dynamic"]
            self.assertEqual(len(dynamic), 6)
            self.assertTrue(all("--shrink-rate" in cmd for cmd in dynamic))
            phased = [cmd for _, cmd in jobs if "--binary" in cmd and
                      cmd[cmd.index("--binary") + 1].endswith("/phased")]
            self.assertEqual(len(phased), 10)
            self.assertEqual(phased[0].count("--binary-arg"), 2)

    def test_missing_resizer_parameters_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            args = SimpleNamespace(
                rob_configs=["dynamic"], predictors=["tage"], types=["phased"],
                results=Path(temp), gem5_binary=Path(temp) / "gem5.opt",
                config=ROOT / "configs" / "run_o3.py",
            )
            with self.assertRaisesRegex(ValueError, "non-null settings"):
                runner.build_runs(args, runner.load_json("baseline.json"),
                                  runner.load_json("resizer.json"), runner.load_json("workloads.json"))

    def test_multiple_stats_blocks_and_normalized_metrics(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / "results" / "dynamic" / "tage" / "phased" / "phased"
            run.mkdir(parents=True)
            (run / "stats.txt").write_text("""---------- Begin Simulation Statistics ----------
simTicks 100
system.cpu.ipc 0.1
---------- End Simulation Statistics ----------
---------- Begin Simulation Statistics ----------
simTicks 200000
simFreq 1000000000000
system.cpu.numCycles 5000
system.cpu.commitStats0.numInsts 8000
system.cpu.ipc 1.6
system.cpu.cpi 0.625
system.cpu.commit.branchMispredicts 1000
system.cpu.rob.squashedIssuedInsts 1500
system.cpu.rob.squashedInsts 2000
system.cpu.rob.squashedExecutedInsts 300
system.cpu.robResizer.branches 4000
system.cpu.robResizer.windows 80
system.cpu.robResizer.shrinks 3
system.cpu.robResizer.grows 3
system.cpu.robResizer.instsFull 3000
system.cpu.robResizer.instsRestricted 5000
---------- End Simulation Statistics ----------
""")
            (run / "run.json").write_text(json.dumps({"status": "success", "wall_seconds": 5.2, "identity": {"gem5_sha256": "abc"}}))
            (run / "simulator.log").write_text("kind=phased phases=6 checksum=ab1efc\n")
            rows = collector.collect(Path(temp) / "results")
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["sim_ticks"], 200000)
            self.assertEqual(row["ipc"], 1.6)
            self.assertEqual(row["branch_mispredict_rate"], 0.25)
            self.assertEqual(row["issued_squashes_per_1k_committed"], 187.5)
            self.assertEqual(row["resizer_restricted_fraction"], 0.625)
            self.assertEqual(row["resizer_shrinks"], 3)
            self.assertEqual(row["program_checksum"], "ab1efc")

    def test_stat_parser_drops_incomplete_trailing_dump(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "stats.txt"
            file.write_text("""---------- Begin Simulation Statistics ----------
a 42
---------- End Simulation Statistics ----------
---------- Begin Simulation Statistics ----------
a 900
""")
            self.assertEqual(collector.read_stats(file)["a"], 42)


    def test_runner_writes_manifest_skips_and_retries_when_inputs_change(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "gem5.py").write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib, sys\n"
                "out = pathlib.Path(next(a.split('=', 1)[1] for a in sys.argv if a.startswith('--outdir=')))\n"
                "out.mkdir(parents=True, exist_ok=True)\n"
                "(out/'stats.txt').write_text('simTicks 900\\nsystem.cpu.ipc 1.5\\n')\n"
                "print('kind=predictable checksum=ef123a')\n"
            )
            (root / "gem5.py").chmod(0o755)
            (root / "config.py").write_text("# stub for metadata test\n")
            (root / "bench").write_text("v1\n")
            outdir = root / "results" / "small" / "local" / "predictable" / "simple"
            cmd = [str(root / "gem5.py"), f"--outdir={outdir}",
                   str(root / "config.py"), "--rob-config", "small",
                   "--bp", "local", "--binary", str(root / "bench")]
            self.assertEqual(runner.run_one(outdir, cmd, gem5_root=root), "success")
            self.assertEqual(runner.run_one(outdir, cmd, gem5_root=root), "skipped")
            record = json.loads((outdir / "run.json").read_text())
            self.assertEqual(record["status"], "success")
            self.assertIn("workload_sha256", record["identity"])
            self.assertEqual(collector.collect(root / "results")[0]["program_checksum"], "ef123a")
            (root / "bench").write_text("v2\n")
            self.assertEqual(runner.run_one(outdir, cmd, gem5_root=root), "success")


if __name__ == "__main__":
    unittest.main()
