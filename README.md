# Dynamic ROB Resizing in gem5

This project studies how reorder buffer (ROB) size affects performance and wasted energy, and tests a dynamic resizing mechanism that shrinks the ROB when branch prediction gets unreliable.

## Problem

Larger ROBs let a processor find more parallel work, but only when branch prediction is accurate. On unpredictable, branch-heavy code, a large ROB lets the processor run further down the wrong path before a misprediction is caught. All of that work gets squashed, wasting time and power.

The goal is to find where increasing ROB size stops helping performance and starts driving up wasted energy.

## Approach

We add a finite state machine (FSM) to gem5's O3 CPU that monitors branch prediction accuracy at runtime:

- **Low accuracy:** shrink the ROB and issue queues to 64 entries
- **High accuracy:** restore them to 256 entries

This limits wasted speculative work during unpredictable phases while keeping the performance of a large ROB elsewhere.

## Experiments

| Variable | Values |
|----------|--------|
| ROB size | 64, 128, 256, 512, dynamic (64 to 256) |
| Branch predictor | TAGE (high accuracy), 2-bit local (low accuracy) |
| Workload | branch-heavy / unpredictable, linear / predictable |

Issue queues and load/store queues scale proportionally with ROB size.

## Metrics

- **IPC**: performance
- **Squashed instructions per 1,000 committed instructions**: wasted speculative work
- **Power proxy**: execution time combined with squashed instruction volume, to estimate wasted dynamic power

The target result: the dynamic configuration matches the IPC of a static 256-entry ROB, with the waste of a 64-entry ROB during unpredictable code.