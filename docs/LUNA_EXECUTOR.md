# Luna Max Mechanical Executor Manual

Luna Max executes only a frozen architect specification. It does not interpret benchmark intent.

## Allowed sequence

1. Run `git status --short` and record the current branch/HEAD.
2. Run `python scripts/luna_executor.py doctor --config <frozen-run-config>`.
3. If doctor prints `NOT_READY`, stop and report the failed checks exactly.
4. If doctor prints `READY`, run only the exact benchmark command supplied in the user/Web GPT task book.
5. Periodically run `python scripts/luna_executor.py status --run-dir <run-dir>`.
6. If the runner exits, run `status`; use only the documented resume command for the same run directory.
7. On completion, run the frozen validator, scorer and report commands from the task book.
8. Run `git diff` and `git status`.
9. Commit or push only when the user task explicitly authorizes it and only with task-related files.

## Forbidden actions

- Edit task, scorer, benchmark, generation-profile, retry-policy or model-selection manifests.
- Change timeout, retry, circuit-breaker, keep-alive or warm-up values.
- Download, delete, rename or replace models.
- Add tasks, assets, probes or models.
- Fix design/scorer bugs and silently continue.
- Re-run valid inference because a scorer changed.
- Decide model inclusion, ranking, dominance, retention or supplementary tests.
- Start a next phase not explicitly present in the frozen plan.

## Failure handling

- A task/model/scorer/runtime error is recorded by the executor; Luna does not reinterpret it.
- Repeated Ollama connection refusal is handled by the configured circuit breaker. If recovery is exhausted, retain the checkpoint and stop.
- A design-level ambiguity, digest mismatch, manifest/hash mismatch or unresolved placeholder requires immediate stop and escalation to the user/Web GPT.
- Never report `READY` when doctor reports `NOT_READY`.
