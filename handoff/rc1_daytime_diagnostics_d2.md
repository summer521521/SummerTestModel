# SummerTestModel RC1 Daytime Diagnostics D2

## Scope and evidence boundary

- benchmark_version: `1.0-rc1`
- purpose: direct HTTP Transport Truth Test for the R2 `PERF_01` terminal-record anomaly.
- runner commit observed: `31c61dcfd9ebc6ef5173b93299c95525bab30e9f`
- branch: `benchmark-rebuild-prep`
- Ollama: `0.32.6`; preflight and postflight `/api/version` were HTTP 200.
- formal baseline, calibration R3, cloud benchmark, model changes, server configuration changes, and tracked code changes: **not performed**.

Complete private request JSON, response headers, raw body bytes, NDJSON, stderr, adapter evidence, and diagnostic scripts remain under the ignored path `private_runs/diagnostics_d2_20260809/`. No private task text or model output is reproduced here.

## Transport truth

The core direct probes used `curl.exe` against `http://127.0.0.1:11434`. Streaming responses used `application/x-ndjson` with `Transfer-Encoding: chunked`; the non-stream response used `application/json; charset=utf-8`. All listed requests had curl exit code 0 and zero malformed JSON lines.

| probe | model | endpoint | stream | sampling | num_predict | HTTP | curl exit | raw bytes | raw lines / parsed | done_seen | done_reason | eval_count | clean_eof | wall_seconds |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| `A_BASIC_NEMOTRON` | `nemotron-3-nano:4b` | `/api/generate` | true | temperature 0 | 16 | 200 | 0 | 496 | 2 / 2 | true | `stop` | 2 | true | 4.547 |
| `B_DIRECT_PERF_TEMP0` | `nemotron-3-nano:4b` | `/api/generate` | true | temperature 0 | 256 | 200 | 0 | 3467 | 31 / 31 | false | — | — | true | 3.187 |
| `D_NATIVE_PERF` | `nemotron-3-nano:4b` | `/api/generate` | true | native | 256 | 200 | 0 | 2864 | 10 / 10 | true | `stop` | 10 | true | 1.609 |
| `E0_TEMP0` | `nemotron-3-nano:4b` | `/api/generate` | true | temperature 0 | 256 | 200 | 0 | 3468 | 31 / 31 | false | — | — | true | 2.093 |
| `E01_TEMP01` | `nemotron-3-nano:4b` | `/api/generate` | true | temperature 0.1 | 256 | 200 | 0 | 3469 | 31 / 31 | false | — | — | true | 1.953 |
| `E05_TEMP05` | `nemotron-3-nano:4b` | `/api/generate` | true | temperature 0.5 | 256 | 200 | 0 | 3467 | 31 / 31 | false | — | — | true | 2.156 |
| `E10_TEMP10` | `nemotron-3-nano:4b` | `/api/generate` | true | temperature 1.0 | 256 | 200 | 0 | 3100 | 12 / 12 | true | `stop` | 12 | true | 2.422 |
| `NONSTREAM_PERF_TEMP0` | `nemotron-3-nano:4b` | `/api/generate` | false | temperature 0 | 256 | 200 | 0 | 410 | 1 / 1 | false | — | — | true | 2.047 |

For the failing streaming rows, the final record had `done=false`, no `done_reason`, no `eval_count`, and response content was present. The raw body was valid through the final byte. This is an HTTP clean EOF with no terminal NDJSON record, not a curl process failure, malformed final bytes, or client timeout.

## Adapter comparison

Probe C used the unmodified current `scripts/ollama_adapter.py` immediately after the saved direct B evidence.

| property | direct B | adapter C |
| --- | --- | --- |
| endpoint | `/api/generate` | `/api/generate` |
| semantic request | same | same |
| exact JSON equality | — | false only because direct uses `keep_alive: "5m"`, adapter uses `keep_alive: 300` |
| normalized request equality | true | true |
| status | `stream_interrupted` | `stream_interrupted` |
| terminal record | absent | absent |
| raw line evidence | 31 lines / 3467 bytes | adapter persisted 0 chunks on exception |
| classification | — | `SERVER_OR_MODEL_RUNTIME_BEHAVIOR` |

The adapter did not expose raw bytes or response headers after its `stream_interrupted` return, but its endpoint, `think`, options, and semantic request matched direct B. Direct HTTP also lacked `done=true`, so `ADAPTER_READ_OR_PARSE_BUG` is not supported.

## Sampling matrix and seed interaction

| probe | sampling | done_seen | done_reason | eval_count | transport classification |
| --- | --- | ---: | --- | ---: | --- |
| `D_NATIVE_PERF` | native defaults | true | `stop` | 10 | normal terminated NDJSON |
| `E0_TEMP0` | temperature 0 | false | — | — | `OLLAMA_TERMINAL_RECORD_MISSING` |
| `E01_TEMP01` | temperature 0.1 | false | — | — | `OLLAMA_TERMINAL_RECORD_MISSING` |
| `E05_TEMP05` | temperature 0.5 | false | — | — | `OLLAMA_TERMINAL_RECORD_MISSING` |
| `E10_TEMP10` | temperature 1.0 | true | `stop` | 12 | normal terminated NDJSON |
| `F1_TEMP0_SEED42` | temperature 0 + seed 42 | false | — | — | `OLLAMA_TERMINAL_RECORD_MISSING` |
| `F2_TEMP01_SEED42` | temperature 0.1 + seed 42 | false | — | — | `OLLAMA_TERMINAL_RECORD_MISSING` |

Seed did not restore terminal behavior. The observed separation is not specifically “zero versus every positive temperature”: 0, 0.1, and 0.5 failed, while 1.0 and the native/default path completed.

## Cross-model direct controls

All controls used the same private `PERF_01` task text and were sent directly with curl; no task text is included here.

| model | sampling | HTTP / curl | raw lines | done_seen | transport classification |
| --- | --- | --- | ---: | ---: | --- |
| `qwen3.5:4b` | temperature 0 | 200 / 0 | 31 | false | `OLLAMA_TERMINAL_RECORD_MISSING` |
| `qwen3.5:4b` | native | 200 / 0 | 31 | false | `OLLAMA_TERMINAL_RECORD_MISSING` |
| `phi4-mini:latest` | temperature 0 | 200 / 0 | 31 | false | `OLLAMA_TERMINAL_RECORD_MISSING` |
| `phi4-mini:latest` | native | 200 / 0 | 31 | false | `OLLAMA_TERMINAL_RECORD_MISSING` |

The fixed PERF path is therefore `MULTI_MODEL_REPRODUCIBLE`; it is not `MODEL_SPECIFIC_ONLY`. Nemotron differs in that its native/default and temperature 1.0 probes completed.

## Output-length and prompt controls

| probe | num_predict | HTTP / curl | raw bytes | done_seen | done_reason | eval_count |
| --- | ---: | --- | ---: | ---: | --- | ---: |
| `L16_TEMP0` | 16 | 200 / 0 | 3691 | true | `length` | 16 |
| `L32_TEMP0` | 32 | 200 / 0 | 3465 | false | — | — |
| `L64_TEMP0` | 64 | 200 / 0 | 3465 | false | — | — |
| `L128_TEMP0` | 128 | 200 / 0 | 3469 | false | — | — |
| `L256_TEMP0` | 256 | 200 / 0 | 3466 | false | — | — |

The transition is repeatable between 16 and 32 tokens: `OUTPUT_LENGTH_INTERACTION`.

The ordinary 100-word benchmark-explanation control completed with `done_reason=stop` and `eval_count=98` under temperature 0. Both explicit 32-word and 64-word repetition controls lacked a terminal record. This supports `PROMPT_DETERMINISM_INTERACTION_SUSPECT` for the repeated-generation task shape.

The non-stream control returned one valid JSON body with HTTP 200 and curl exit 0, but it also had `done=false`, no `done_reason`, no `eval_count`, and no `total_duration`. This independently rules against a streaming-only parser explanation.

## Modelfile defaults

Only selected parameter metadata is reported; complete Modelfiles remain private.

| model | temperature | top_k | top_p | min_p | repeat_penalty | stop declarations | template |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `nemotron-3-nano:4b` | 1 | — | 1 | — | — | none observed | present |
| `qwen3.5:4b` | 1 | 20 | 0.95 | — | — | none observed | present |
| `phi4-mini:latest` | not declared | not declared | not declared | not declared | not declared | none observed | present |

## Cold versus warm timing

Each model was explicitly unloaded through direct HTTP, then given one short cold request and one immediate warm repeat.

| model | cold load_duration (s) | warm load_duration (s) | cold wall (s) | warm wall (s) | cold-warm wall delta (s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `qwen3.5:4b` | 4.898 | 1.267 | 5.344 | 1.438 | 3.906 |
| `nemotron-3-nano:4b` | 3.213 | 0.938 | 3.406 | 1.110 | 2.296 |

`COLD_LOAD_SEPARATION_CONFIRMED`: `load_duration` and client wall time both distinguish cold from warm requests in this diagnostic sample.

## Timing field sanity

The normal direct standard-library streaming timing probe completed successfully (this probe did not use the adapter):

- client wall: `1.296 s`
- first NDJSON record / first final content / terminal record: `1.296 s`
- server `total_duration`: `1.273217 s`
- client minus server total: `+0.022783 s`
- server `load_duration`: `1.120755 s`
- server `prompt_eval_duration`: `0.114502 s`
- server `eval_duration`: `0.026213 s`

The client and server timings are close but not identical, as expected from transport and process overhead.

## D2 conclusions

Assigned labels:

- `OLLAMA_TERMINAL_RECORD_MISSING`
- `SAMPLING_POLICY_INTERACTION_CONFIRMED`
- `PROMPT_DETERMINISM_INTERACTION_SUSPECT`
- `OUTPUT_LENGTH_INTERACTION`
- `MULTI_MODEL_REPRODUCIBLE`
- `COLD_LOAD_SEPARATION_CONFIRMED`

Not supported by the direct evidence:

- `ADAPTER_READ_OR_PARSE_BUG`
- `HTTP_TRANSPORT_ABORT`
- `MODEL_SPECIFIC_ONLY`

At the HTTP boundary, the D2 evidence supports a cleanly completed transfer whose server response lacks the terminal NDJSON record for the failing task shape. The evidence does not authorize changing sampling policy, token budget, timeout, preload policy, calibration, or benchmark design; this handoff is diagnostic only and stops before R3.

## Preservation

- `private_runs/calibration`, `private_runs/calibration_r2`, and `private_runs/diagnostics_20260809` were preserved.
- No model was downloaded, deleted, updated, or re-quantized.
- No formal baseline or cloud benchmark was run.
- No public result JSONL was created.
- retention: `UNASSESSED`
