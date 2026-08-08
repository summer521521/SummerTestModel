# Legacy Cleanup Plan

No historical benchmark data was deleted or moved.

| Path | Type | Tracked | Remote history | Size bytes | Recommended action | Reason | Recovery |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| `benchmark_20260629/results/` | V1 evidence | yes | yes (`origin/main` at audit start) | 194729 | Preserve historical evidence | Contains original raw/results | Restore from Git commit `ea68462` |
| `benchmark_20260629/runs/20260730_incremental/` | Incremental evidence | yes | yes (`origin/main` at audit start) | 5161977 | Preserve historical evidence | Independent resumable run | Restore from Git commit `ea68462` |
| `benchmark_20260629/runs/20260731_v2_comprehensive/` | V2 evidence | yes | yes (`origin/main` at audit start) | 79649698 | Preserve historical evidence | Immutable inference evidence and derived scores | Restore from Git commit `ea68462` |
| `benchmark_20260629/runs/20260731_v2_smoke/` | Smoke evidence | yes | yes (`origin/main` at audit start) | 7139553 | Await architect decision | Distinct from root smoke run | Restore from Git commit `ea68462` |
| `benchmark_20260731_v2_smoke/` | Smoke evidence | yes | yes (`origin/main` at audit start) | 7139604 | Await architect decision | Distinct run ID/content | Restore from Git commit `ea68462` |
| `benchmark_20260629/scripts/benchmark.py` | Legacy runner/scorer | yes | yes (`origin/main` at audit start) | 25394 | Do not use for future code scoring | Executes model output in process | Restore from Git commit `ea68462` |
| `benchmark_20260629/scripts/benchmark_v2.py` | Coupled V2 runner | yes | yes (`origin/main` at audit start) | 70626 | Reuse persistence ideas only | Contains frozen old tasks/scorers | Restore from Git commit `ea68462` |
| `**/__pycache__/` | Generated cache | no (ignored) | no | rebuildable | Safe to omit | Python bytecode only | Re-run Python |

True deletion or migration requires Web GPT/user approval.
