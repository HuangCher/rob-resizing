# Workloads

The benchmark programs haven't been chosen yet. Two kinds are needed:

- **unpredictable**: branch-heavy code with data-dependent branches.
- **predictable**: mostly linear code with few, regular branches.

When they're chosen:

1. Put the sources in `workloads/src/<name>/`.
2. Build static binaries for the target ISA into `workloads/bin/` (git ignores this folder).
3. Add each one to `experiments/workloads.json` under its type:

   ```json
   {"name": "<name>", "binary": "workloads/bin/<name>", "args": []}
   ```
