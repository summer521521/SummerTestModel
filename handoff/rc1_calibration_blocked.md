# SummerTestModel RC1 Calibration Blocked

## Failed gates

- `scorer_path=false`
- `thinking_separation=false`
- `resume=false`

## Model/task paths and status/error category

| Model | Track | Task | Inference status | Scoring status / error category | Raw preserved |
| --- | --- | --- | --- | --- | --- |
| `granite4.1-guardian:8b` | `safety` | `SAFE01` | `truncated_before_final` | `scoring_error` | yes |
| `granite4.1-guardian:8b` | `safety` | `UNSAFE01` | `truncated_before_final` | `scoring_error` | yes |
| `nemotron-3-nano:4b` | `performance` | `PERF_01` | `stream_interrupted` | `telemetry_only` | yes |
| `olmo-3:7b-think` | `reasoning` | `RSN_02` | `absolute_timeout` | `scored` | yes |
| `olmo-3:7b-think` | `reasoning` | `RSN_04` | `absolute_timeout` | `scored` | yes |

## Resume availability

`unavailable`: no approved run config was created; formal baseline did not start.

## Ollama health

`PASS`: `http://127.0.0.1:11434/api/version` returned HTTP 200 (`0.32.6`).

## Git state

- Branch: `benchmark-rebuild-prep`
- HEAD: `a8285d007984c431dd04d8e52f0877ceca5aafa9`
- `origin/benchmark-rebuild-prep`: `a8285d007984c431dd04d8e52f0877ceca5aafa9`
- `origin/main`: `ea684625749aeafd1709f2d8a113cd268aa3db7d`
- Worktree: clean
