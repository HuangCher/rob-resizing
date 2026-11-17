# Dynamic ROB Resizing in gem5

This project investigates how reorder buffer (ROB) size and branch predictability affect the performance and wasted speculative work of an out-of-order processor. We also evaluate a mechanism that dynamically reduces the usable ROB capacity when branch prediction becomes unreliable.

## Motivation

Larger ROBs can expose more instruction-level parallelism, but they also allow more instructions to execute speculatively. When a branch is mispredicted, younger instructions are squashed, wasting resources. The goal is to determine when increasing ROB size stops improving performance and whether dynamic resizing can reduce this waste.

## Approach

We modify gem5's RISC-V O3 CPU to monitor branch mispredictions over instruction windows. A finite state machine (FSM) switches between a **256-entry ROB** and a **64-entry restricted ROB** based on configurable thresholds. Associated instruction-window resources are also restricted during low-accuracy phases.

This models capacity restrictions, not physical power gating.

## Experiments

| Variable | Configurations |
| --- | --- |
| ROB size | 64, 128, 256, 512, dynamic (64–256) |
| Branch predictor | TAGE, 2-bit local |
| Workload | Predictable, unpredictable, phased |

Three deterministic RISC-V C microbenchmarks test different branch behaviors:

- **Predictable:** Frequent branches with regular outcomes.
- **Unpredictable:** Data-dependent branches with approximately balanced outcomes.
- **Phased:** Alternates predictable and unpredictable behavior to test the FSM's response.

The complete experiment matrix contains **30 simulations**.

## Metrics

- **IPC/CPI:** Execution performance.
- **Branch misprediction rate:** Prediction accuracy.
- **Squashed instructions per 1,000 committed instructions:** Wasted speculative work.
- **Squashed issued/executed instructions:** Additional speculative-work proxies.
- **FSM transitions and restricted-state duration:** Dynamic resizing behavior.

Squashed-work measurements are *proxies* for potential energy waste; they are not direct measurements of power or energy.

## Running the Experiments

A RISC-V Linux cross-compiler, Python 3, and a compatible gem5 build are required. With the `rob-riscv` Conda environment activated, run from the repository root:

```bash
# Build the RISC-V workloads
bash scripts/build_workloads.sh \
  "$CONDA_PREFIX/bin/riscv64-conda-linux-gnu-gcc" \
  "$CONDA_PREFIX/bin/riscv64-conda-linux-gnu-objdump"

# Validate the experiment tools
python3 -m unittest discover -s tests -v

# Preview the experiment matrix
python3 experiments/run_matrix.py --gem5-root /path/to/gem5 --dry-run

# Run after simulator integration and configuration of FSM thresholds
python3 experiments/run_matrix.py --gem5-root /path/to/gem5

# Collect statistics
python3 analysis/collect.py --results results
```

Run outputs are saved under `results/<rob>/<predictor>/<workload_type>/<workload_name>/`, and aggregated metrics are written to `results/summary.csv`. The `results/` and `workloads/bin/` directories are excluded from version control.

## Preliminary Validation

All three workloads ran successfully on stock gem5 25.1.0.1 with the same O3 CPU and default branch predictor:

| Workload | IPC | Conditional prediction error rate |
| --- | ---: | ---: |
| Predictable | 4.4696 | 0.32% |
| Unpredictable | 1.3495 | 8.94% |
| Phased | 1.9578 | 5.32% |

These results validate the workloads' aggregate branch behavior, **not** the dynamic ROB mechanism. Final performance and speculative-work conclusions require the integrated simulator and full experiment matrix.
