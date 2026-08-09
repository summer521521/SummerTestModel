# SummerTestModel RC1 Final Soak Test S1

- status: `BASELINE_READY`
- benchmark_version: `1.0-rc1`
- purpose: `SOAK_S1_ONLY`
- approval_basis: `CALIBRATION_R3_PASS`
- approval_commit: `edc99b5ebdcebfeb85944e4b8e887adff49092b6`
- formal baseline: not started
- public baseline result: not generated

## Duration and process boundary

- continuous soak wall time: `4006.33` seconds (about 66 minutes 46 seconds)
- Phase A: `1398.00` seconds
- Phase B: `1290.00` seconds
- repeat cycles: 2 independent SOAK_REPEAT_SET cycles, 10 repeat-only records
- process-boundary resume/dedup: `PASS`
- resume probe: `qwen3.5:4b / CORE_FMT_01`, 0 new inference; state and raw counts unchanged

Phase A and Phase B used independent Python runner processes. All checkpoints and raw references remained readable after the boundary.

## Models and paths

Nine frozen local models were exercised:

`functiongemma:270m`, `qwen3.5:4b`, `olmo-3:7b-think`, `deepseek-ocr:latest`, `qwen3-embedding:latest`, `granite4.1-guardian:8b`, `qwen3.5:9b`, `gemma4:e4b`, `phi4-mini:latest`.

The run covered tiny tools, general/code, native thinking, CPU-offload OCR, vision/OCR, embedding, safety, 32K context, resource-heavy multimodal, and cold/warm performance. The frozen qwen3.5:9b plan included `VIS_08`, so it was executed.

## Runtime telemetry

- model sequence transitions: 16
- preload records: 36 completed; payload shape valid
- process-close unloads: 36; post-model `ollama ps` checks showed no residual model
- tasks attempted: 37
- raw records saved: 37
- score records saved privately: 37; no soak score values are published here
- semantic/protocol failure count: 10 (count only)
- timeouts: 0
- truncations: 2; both were terminal model evidence with raw preserved
- runtime anomalies: 0
- stream interrupted before output: 0
- stream interrupted after output: 0
- scoring errors: 0
- runner exceptions: 0
- infrastructure retries: 0
- circuit-breaker openings: 0
- duplicate inference: 0
- missing raw references: 0
- model digest drift: 0
- manifest/hash drift: 0

Cold/warm performance completed in the same frozen runner pair: the cold record had preload metadata, the warm record did not issue another preload, and both had terminal/eval/total timing metadata.

Live resource observations included CPU/GPU mixed execution for `olmo-3:7b-think` and `deepseek-ocr:latest`, plus GPU-heavy qwen3.5:9b execution. Final Ollama health was HTTP 200, version `0.32.6`, with no loaded model.

## Isolation and Git state

- private run path: `private_runs/soak_s1`
- repeat paths: `private_runs/soak_s1/repeat_cycles/soak_repeat_01` and `private_runs/soak_s1/repeat_cycles/soak_repeat_02`
- private isolation: `PASS`; private benchmark and private run files are ignored and not Git-tracked
- tracked code changes during S1: none
- branch: `benchmark-rebuild-prep`
- HEAD before handoff: `edc99b5ebdcebfeb85944e4b8e887adff49092b6`
- main: unchanged at `ea684625749aeafd1709f2d8a113cd268aa3db7d`
- retention: `UNASSESSED`

One local wrapper launch attempt failed before entering the Python runner; it created no state/raw mutation. The performance pair then completed through the existing frozen runner path. No benchmark, scorer, model inventory, model files, or Ollama configuration was changed.

This handoff contains only derived counts and runtime metadata; no private task content or model payload is included.
