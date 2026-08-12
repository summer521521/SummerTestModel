# Legacy Cleanup Plan

No historical benchmark data was deleted or moved. Ignored Python bytecode/test caches are the only content classified as immediately disposable; all logs, raw evidence, smoke runs, manifests, public snapshots, and legacy scripts remain available for audit or recovery.

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
| `.pytest_cache/` | Generated test cache | no (ignored) | no | rebuildable | Safe to omit | Test-run cache only | Re-run tests |
| `private_runs/rc1_baseline_20260809/` | Immutable RC1 local evidence | no (ignored) | no | local-only | Preserve; never publish raw | Canonical 39-model baseline and resume state | Local backup/private run only |
| `private_runs/rc1_cloud_comparison_20260812/` | Immutable cloud reference evidence | no (ignored) | no | local-only | Preserve; never publish raw | Canonical cloud streamed evidence and state | Local backup/private run only |
| `public_results/rc1_baseline_20260809.jsonl` | Original sanitized RC1 derivation | yes | current branch history | public | Preserve superseded snapshot | Historical scorer output before offline fix | Git commit `cca5505` |
| `public_results/rc1_baseline_20260809.scorer-1.0-rc1.1.jsonl` | Current sanitized RC1 derivation | pending | no at update time | public | Publish | Fixed scorer sidecar; raw unchanged | Regenerate offline from private raw |

True deletion or migration of historical evidence still requires explicit user approval.
