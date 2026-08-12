# SummerTestModel RC1 Daytime Diagnostics D1

## Scope and execution boundary

- benchmark_version: `1.0-rc1`
- diagnostic purpose: locate the remaining R2 `thinking_separation` and `performance_path` failures.
- runner commit observed: `4cbb54a088d638969b2c1c3adf9068ede2fcce93`
- branch: `benchmark-rebuild-prep`
- Ollama: `0.32.6`; API health was HTTP 200 before and after the probes.
- formal baseline: **not run**.
- calibration rerun: **not run**.
- cloud benchmark: **not run**.
- tracked benchmark assets, scorer semantics, assignments, profiles, and runtime policy: **not modified**.

Private raw responses, stream chunks, and diagnostic logs remain in the ignored diagnostic area `private_runs/diagnostics_20260809/`. No private payload is reproduced here.

## Existing R2 audit

The two R2 private directories were preserved. R2 raw records contain the request parameters below, but do not persist endpoint or transport-attempt fields; those fields are reported as `not_persisted_in_r2_record` rather than inferred. Wall time is reconstructed only from the corresponding R2 `events.jsonl` timestamps.

| model | task | endpoint in R2 raw | think | num_ctx | num_predict | temperature | inference status | termination | chunks (thinking/final) | eval_count | wall_seconds | logical attempt events |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |
| `qwen3.5:4b` | `CAL_R2_THINK_PROBE` | not persisted | true | 4096 | 256 | 0 | `truncated_before_final` | `length` | 231 (230/0) | 256 | 11.988 | 1 |
| `nemotron-3-nano:4b` | `PERF_01` first | not persisted | false | 4096 | 256 | 0 | `stream_interrupted` | — | 0 (0/0) | — | 4.906 | 2 |
| `nemotron-3-nano:4b` | `PERF_01` revalidation | not persisted | false | 4096 | 256 | 0 | `stream_interrupted` | — | 0 (0/0) | — | 4.033 | 2 |

## Thinking separation diagnostics

All Qwen probes used the frozen calibration-only task text, `/api/generate`, streaming, top-level `think=true`, `num_ctx=4096`, and temperature 0 unless marked `native`.

| probe | endpoint | num_predict | sampling | thinking_present | final_present | done_reason | eval_count | wall_seconds |
| --- | --- | ---: | --- | ---: | ---: | --- | ---: | ---: |
| `QWEN_T256` | `/api/generate` | 256 | temperature 0 | true | false | `length` | 256 | 11.687 |
| `QWEN_T512` | `/api/generate` | 512 | temperature 0 | true | false | `length` | 512 | 13.094 |
| `QWEN_T1024` | `/api/generate` | 1024 | temperature 0 | true | false | `length` | 1024 | 23.360 |
| `QWEN_T2048` | `/api/generate` | 2048 | temperature 0 | true | true | `stop` | 1318 | 28.531 |
| `QWEN_NATIVE` | `/api/generate` | 1024 | native | true | false | `length` | 1024 | 22.656 |
| `CONTROL_MINICPM5_THINK` (`openbmb/minicpm5:Q4_K_M`) | `/api/generate` | 1024 | temperature 0 | false | true | `stop` | 247 | 4.110 |

The minimum tested `num_predict` that produced a final answer for Qwen was **2048**. The 256/512/1024 runs all ended with `length` after emitting thinking only. Native sampling at 1024 reproduced the no-final result, so the data do not support `SAMPLING_POLICY_SUSPECT` for the thinking issue. A chat comparison was not needed: generate produced a final at 2048.

Thinking classification:

- `BUDGET_LIMIT_LIKELY` — primary classification.
- `MODEL_SPECIFIC_THINKING_BEHAVIOR` — Qwen emitted thinking and exhausted the lower budgets; the inventory-approved Minicpm5 control emitted no thinking and returned a final.
- `THINKING_PIPELINE_WORKS_ON_CONTROL_MODEL` — limited to the control request’s clean final completion; the control did not emit a thinking field, so this is not a claim that both models expose identical thinking behavior.
- Not supported by D1: `SAMPLING_POLICY_SUSPECT`, `ENDPOINT_SPECIFIC_SUSPECT`, and `THINKING_RUNTIME_UNRESOLVED`.

## Performance-path diagnostics

All Nemotron probes used the frozen private `PERF_01` task text, `num_ctx=4096`, and `think=false`. `healthy(200/0.32)` means the `/api/version` health check after the probe returned HTTP 200 with Ollama 0.32.6.

| probe | model | endpoint | stream | num_predict | sampling | status | done_seen | eval_count | wall_seconds | health_after |
| --- | --- | --- | ---: | ---: | --- | --- | ---: | ---: | ---: | --- |
| `NEMOTRON_P1_BASIC` | `nemotron-3-nano:4b` | `/api/generate` | true | 16 | temperature 0 | completed | true | 2 | 4.594 | healthy(200/0.32) |
| `NEMOTRON_P2_PERF` | `nemotron-3-nano:4b` | `/api/generate` | true | 64 | temperature 0 | `stream_interrupted` | false | — | 1.984 | healthy(200/0.32) |
| `NEMOTRON_P3_PERF` | `nemotron-3-nano:4b` | `/api/generate` | true | 128 | temperature 0 | `stream_interrupted` | false | — | 0.859 | healthy(200/0.32) |
| `NEMOTRON_P4_PERF` | `nemotron-3-nano:4b` | `/api/generate` | true | 256 | temperature 0 | `stream_interrupted` | false | — | 0.859 | healthy(200/0.32) |
| `NEMOTRON_P5_PERF_NONSTREAM` | `nemotron-3-nano:4b` | `/api/generate` | false | 256 | temperature 0 | body returned; incomplete terminal evidence | false | — | 0.812 | healthy(200/0.32) |
| `NEMOTRON_P6_PERF_NATIVE` | `nemotron-3-nano:4b` | `/api/generate` | true | 256 | native | completed | true | 5 | 1.109 | healthy(200/0.32) |
| `NEMOTRON_P7_PERF_CHAT` | `nemotron-3-nano:4b` | `/api/chat` | true | 256 | temperature 0 | `stream_interrupted` | false | — | 9.015 | healthy(200/0.32) |
| `CONTROL_A_QWEN35_PERF` | `qwen3.5:4b` | `/api/generate` | true | 256 | temperature 0 | `stream_interrupted` | false | — | 3.360 | post-batch healthy(200/0.32) |
| `CONTROL_B_PHI4MINI_PERF` | `phi4-mini:latest` | `/api/generate` | true | 256 | temperature 0 | `stream_interrupted` | false | — | 29.781 | post-batch healthy(200/0.32) |

The fixed-sampling Nemotron and both independent performance controls shared the same incomplete streaming signature: HTTP 200, meaningful final body/chunks, no `done=true`, and no eval telemetry. Native sampling changed the Nemotron result to a short, fully terminated response with `done_reason=stop` and `eval_count=5`. The chat endpoint did not resolve the fixed-sampling streaming behavior. P5 returned a final body, but also lacked `done=true` and eval telemetry, so it is partial endpoint evidence rather than a complete successful inference.

Performance classification:

- `SAMPLING_POLICY_SUSPECT` — primary operational discriminator: native sampling completed while the fixed temperature-0 path did not.
- `GENERAL_STREAMING_OR_ADAPTER_SUSPECT` — both Qwen and Phi4 performance controls reproduced the fixed-sampling incomplete signature; this is not evidence of a Nemotron-only capability failure.
- `STREAMING_SPECIFIC_SUSPECT` — secondary/partial: streaming did not deliver terminal evidence, while non-stream returned a body; the non-stream body itself also lacked terminal/eval evidence.
- Not supported by D1: `NEMOTRON_SPECIFIC_RUNTIME_BEHAVIOR` and an endpoint-only explanation, because `/api/chat` also failed to terminate under the same fixed sampling.

## Server-side evidence

- inspected window: `2026-08-09 06:53:25` through `06:58:28` (+08:00), covering both R2 Nemotron attempts.
- finding for Nemotron: `NO_MATCHING_SERVER_ERROR_FOUND`.
- no matching panic, runner exit, unload failure, EOF/connection reset, CUDA/OOM/allocation, or HTTP 5xx error was found in that window.
- one context-size warning was excluded as unrelated: it occurred next to an embedding-server startup (`--embedding`), not a Nemotron runner failure.
- no Ollama restart or configuration change was performed.

## Preservation and handoff

- R2 evidence in `private_runs/calibration` and `private_runs/calibration_r2` was not deleted, rebuilt, or overwritten.
- No model was downloaded, deleted, updated, re-quantized, or replaced.
- No formal baseline, cloud benchmark, calibration rerun, approved config, or public result JSONL was created.
- Diagnostic raw/chunks/log summaries are ignored and remain private under `private_runs/diagnostics_20260809/`.
- retention: `UNASSESSED`

This D1 handoff records observations and classifications only. It does not authorize or implement an R3 repair.
