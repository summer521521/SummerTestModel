# SummerTestModel RC1 Calibration Repair R2

- Status: `CALIBRATION_R2_BLOCKED`
- Benchmark version: `1.0-rc1`
- Runtime repair commit: `cfe2c0a`
- R2 run: `private_runs/calibration_r2`
- First calibration evidence: `private_runs/calibration` preserved

## Gates

| Gate | Result |
| --- | --- |
| `scorer_path` | PASS |
| `thinking_separation` | FAIL |
| `resume_dedup` | PASS |
| `tool_loop` | PASS |
| `image_path` | PASS |
| `embed_path` | PASS |
| `safety_parser` | PASS |
| `performance_path` | FAIL |
| `raw_persistence` | PASS |

## Failure metadata

- `qwen3.5:4b` / `calibration_probe` / `CAL_R2_THINK_PROBE`: request `think=true` was recorded; thinking was observed; final answer was absent; `inference_status=truncated_before_final`; termination reason `length`; raw preserved.
- `nemotron-3-nano:4b` / `performance` / `PERF_01`: initial execution and one allowed revalidation both ended with `stream_interrupted`; raw preserved.
- `granite4.1-guardian:8b` / `safety` / `SAFE01, UNSAFE01`: request evidence recorded `think=false`; scoring completed without exception; safety predictions were present.

## Offline validation

- Unit suite: `43/43 PASS`
- Phase 3S golden validation: `116/116 PASS`
- Phase 3R validator: `valid=true`
- Python compile check: PASS

## Runtime and Git state

- Ollama: `0.32.6`, API health HTTP 200
- Formal baseline: not run
- Cloud benchmark: not run
- Local model inventory/retention: unchanged / `UNASSESSED`
- Branch: `benchmark-rebuild-prep`
- Worktree: clean
- `origin/main`: `ea684625749aeafd1709f2d8a113cd268aa3db7d` unchanged
