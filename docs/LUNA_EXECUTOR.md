# Luna Max Mechanical Executor Manual (Benchmark 1.0-rc1)

Luna Max executes only a frozen architect specification. It does not interpret benchmark intent.

## Allowed sequence

1. Run `git status --short` and record the current branch/HEAD.
2. Run `python scripts/rc1_runner.py doctor --config <frozen-run-config>`.
3. If doctor prints `NOT_READY`, stop and report the failed checks exactly.
4. Run calibration only when the user/Web GPT task book explicitly authorizes it: `python scripts/rc1_runner.py calibrate --allow-inference --run-dir <private-run-dir>`.
5. If calibration validation fails, stop. Do not create an approved config and do not run the baseline.
6. After a successful calibration, use only the local ignored approved config produced by the launch flow. Never edit the tracked template.
7. Run only the exact command supplied in the task book: `python scripts/rc1_runner.py run-all --allow-inference --config <approved-config> --run-dir <private-run-dir>`.
8. Periodically run `python scripts/rc1_runner.py status --run-dir <private-run-dir>`.
9. If the runner exits, run `status`, then `python scripts/rc1_runner.py resume --allow-inference --config <approved-config> --run-dir <same-private-run-dir>`.
10. On completion, run `python scripts/rc1_runner.py finalize --run-dir <private-run-dir> --output <public-jsonl>` and the frozen validators from the task book.
11. Run `git diff` and `git status`.
12. Commit or push only when the user task explicitly authorizes it and only with task-related files.

`launch` encodes the same sequence (doctor -> calibration -> validation -> local approval -> doctor -> run-all -> finalize), but Luna may invoke it only when the task book explicitly says to do so. `--mock` is reserved for offline engineering tests and never produces benchmark results.

## Forbidden actions

- Edit task, scorer, benchmark, generation-profile, retry-policy or model-selection manifests.
- Change timeout, retry, circuit-breaker, keep-alive or warm-up values.
- Download, delete, rename or replace models.
- Add tasks, assets, probes or models.
- Fix design/scorer bugs and silently continue.
- Re-run valid inference because a scorer changed.
- Decide model inclusion, ranking, dominance, retention or supplementary tests.
- Start a next phase not explicitly present in the frozen plan.

The RC1 policy files are `config/benchmark_manifest.rc1.json`,
`config/generation_profiles.rc1.json`, `config/retry_policy.rc1.json` and
`config/model_execution_plan.rc1.public.json`. The public task and scorer
manifests and the private package manifest are also hash-locked. Together they
define `1.0-rc1`, the 12 track
IDs, local-only candidates at total parameters <=10B, separate thinking and
final answers, no structured-output assistance, one model at a time, and the
frozen transport/circuit values. Doctor remains `NOT_READY` until calibration
has passed and a local ignored approved config exists.

## Failure handling

- A task/model/scorer/runtime error is recorded by the executor; Luna does not reinterpret it.
- Repeated Ollama connection refusal is handled by the configured circuit breaker. If recovery is exhausted, retain the checkpoint and stop.
- A design-level ambiguity, digest mismatch, manifest/hash mismatch or unresolved placeholder requires immediate stop and escalation to the user/Web GPT.
- Never report `READY` when doctor reports `NOT_READY`.
- Do not run Ollama generation during preparation or when the benchmark specification is absent.
