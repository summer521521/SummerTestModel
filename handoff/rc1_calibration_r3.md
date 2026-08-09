# SummerTestModel RC1 Calibration R3 Handoff

- benchmark_version: `1.0-rc1`
- branch: `benchmark-rebuild-prep`
- runner_commit: `c1e295211f31b601c07f3e5f3901469cf4ed584d`
- calibration_result: `CALIBRATION_R3_PASS`
- baseline_run_status: `NOT_RUN_BY_R3_SCOPE`
- formal_baseline: not started
- local_model_inventory: 39
- cloud_models_in_formal_run: 0
- R3 calibration formal items: 12
- R3 thinking probe: 1 calibration-only probe; separated thinking and final fields observed
- scoring_error_count: 0
- infrastructure_failures: 0
- retries beyond the frozen policy: 0
- Ollama: `0.32.6`; `/api/version`: HTTP 200

## Calibration gates

All 14 frozen R3 gates passed:

`native_sampling_request`, `thinking_separation`, `preload_path`, `timing_fields`, `performance_cold_warm`, `performance_comparability_probe`, `tool_loop`, `image_path`, `embed_path`, `safety_parser`, `scorer_path`, `resume_dedup`, `raw_persistence`, `hash_integrity`.

Native sampling policy was recorded as `native_artifact`; ordinary calibration requests did not add forced sampling parameters. Timing evidence and terminal-record metadata were persisted for the formal calibration items. Soft limits remained reporting-only.

## Performance telemetry

The two private telemetry tasks produced four completed records. No telemetry task was scored.

| model | cold eval_count | cold eval_duration_s | cold total_duration_s | warm eval_count | warm eval_duration_s | warm total_duration_s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `nemotron-3-nano:4b` | 191 | 2.628 | 6.187 | 174 | 2.339 | 2.636 |
| `phi4-mini:latest` | 268 | 3.309 | 7.195 | 196 | 2.407 | 2.641 |

All four records had terminal evidence and completed Ollama metadata. Warm `eval_count` values were 174 and 196, both meeting the frozen comparability threshold.

The shared private telemetry task content is represented publicly only by its SHA-256:

`PERF_COLD_01`, `PERF_WARM_01`: `9ddb99f6aa128001d1697995897f4942cf7a96b7606e55527e74a90fce223777`

## Native runtime and reference scaffold

- Required preload probes passed for `nemotron-3-nano:4b` and `qwen3.5:4b`.
- Request/first-output/final-output/terminal timing fields passed validation.
- Reference scaffold added at `docs/model_reference_policy.md`, `config/model_reference.schema.json`, and `models/reference/`; no fabricated model reference data was added.
- The public task manifest remains 116 scored tasks plus 2 telemetry-only tasks and 1 diagnostic task; the 116 capability-scored task definitions and scorer semantics were not changed by R3.

## Verification and isolation

- Unit tests: 49 passed.
- RC1 golden validation: 116/116 full-score cases passed; code cases: 80/80.
- Phase3R validator: valid, with zero reported integrity errors.
- Resume/dedup validation: passed; terminal logical-key counts were unchanged.
- Private run path: `private_runs/calibration_r3`
- Private benchmark and private run files are ignored and are not Git-tracked.
- Public baseline result: not generated because R3 scope stops after calibration.
- Retention: `UNASSESSED`
- `main` remains unchanged at `ea684625749aeafd1709f2d8a113cd268aa3db7d`.

This handoff is limited to derived metadata and aggregate telemetry; no private payload is included.
