# SummerTestModel RC1 Baseline Night 4 Handoff

Status: NIGHT4_COMPLETE

Formal baseline status: COMPLETE AFTER NIGHT 4; PUBLIC RESULT GENERATED BELOW

Benchmark: 1.0-rc1

Target: approximately 9 hours

Formal run: `private_runs/rc1_baseline_20260809`

Branch: `benchmark-rebuild-prep`

Main: unchanged at `ea684625749aeafd1709f2d8a113cd268aa3db7d`

## Night 4 execution

- Start: 2026-08-12 08:06:50 +08:00
- End: 2026-08-12 13:13:39 +08:00
- Elapsed: 18,409 seconds (5.11 hours; handoff written shortly after model exit)
- Models touched and completed: 17 / 17
- Night 4 logical records: 986
- Night 4 records/hour: approximately 193
- Falcon recovery: 68 / 68
- Remaining model scopes after Night 4: 0

Completed Night 4 scopes, in frozen order:

1. `hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M` (recovered 8 records)
2. `qwen3-vl:8b`
3. `lfm2.5:8b`
4. `nemotron-3-nano:4b`
5. `minicpm-v4.6:latest`
6. `openbmb/minicpm5:Q4_K_M`
7. `granite4.1:8b`
8. `granite4:7b-a1b-h`
9. `ministral-3:8b`
10. `mistral:7b`
11. `olmo-3:7b-instruct`
12. `deepscaler:1.5b`
13. `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL`
14. `huggingface.co/llmware/phi-4-mini-gguf:latest`
15. `rnj-1:latest`
16. `smollm2:1.7b`
17. `hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M`

## Per-model timing metadata

| Model | Records | Wall seconds |
| --- | ---: | ---: |
| Falcon-H1R | 8 | 193 |
| qwen3-vl:8b | 80 | 9,563 |
| lfm2.5:8b | 62 | 369 |
| nemotron-3-nano:4b | 68 | 426 |
| minicpm-v4.6 | 80 | 472 |
| openbmb/minicpm5 | 62 | 987 |
| granite4.1:8b | 52 | 365 |
| granite4:7b-a1b-h | 52 | 95 |
| ministral-3:8b | 70 | 525 |
| mistral:7b | 52 | 195 |
| olmo-3:7b-instruct | 52 | 486 |
| deepscaler:1.5b | 62 | 1,158 |
| SmolLM3-3B | 62 | 1,217 |
| phi-4-mini | 52 | 172 |
| rnj-1:latest | 52 | 249 |
| smollm2:1.7b | 50 | 88 |
| granite-vision-4.1-4b | 70 | 125 |

## Night 4 track timing aggregates

| Track | Records | Total seconds | Mean | Median | P90 |
| --- | ---: | ---: | ---: | ---: | ---: |
| code | 128 | 4,068 | 31.8 | 11 | 60 |
| general | 384 | 2,951 | 7.7 | 2 | 16 |
| long_context_32k | 30 | 422 | 14.1 | 5 | 17 |
| long_context_8k | 32 | 112 | 3.5 | 3 | 7 |
| medical | 6 | 15 | 2.5 | 2 | 6 |
| ocr | 40 | 509 | 12.7 | 6 | 37 |
| performance | 32 | 221 | 6.9 | 6.5 | 12 |
| reasoning | 70 | 5,367 | 76.7 | 14 | 129 |
| tools | 130 | 1,161 | 8.9 | 3 | 18 |
| translation | 102 | 1,282 | 12.6 | 2.5 | 16 |
| vision | 32 | 264 | 8.2 | 2 | 21 |

All timing values are aggregate runtime metadata only; no prompt, answer,
thinking, ground truth, image, tool fixture, or embedding data is included.

## Integrity and classifications

- Cumulative planned/accounted models: 39 / 39
- Cumulative logical records: 1,938
- Cumulative raw records: 1,938
- Missing raw: 0
- Duplicate logical keys: 0
- Night 4 infrastructure failures: 0
- Night 4 runner exceptions: 0
- Night 4 scoring errors: 3 (per-task evidence; no global scorer wiring failure)
- Night 4 absolute timeouts: 2
- Night 4 truncation-related records: 21 (`truncated` 19, `truncated_before_final` 2)
- Night 4 runtime anomaly flags: 2
- Night 4 infra retries: 0
- Circuit-breaker openings: 0

Cumulative classification counts include valid model/runtime evidence:

- Absolute timeouts: 7
- Truncation-related: 104 (`truncated` 66, `truncated_before_final` 38)
- Scoring errors: 3
- Runtime anomaly flags: 19

## Environment snapshot

- Ollama CLI/API: 0.32.6
- Final API health: HTTP 200
- Formal baseline: 39 local models, 0 cloud models
- Practical local environment was not strictly controlled
- Windows pending maintenance/restart metadata and other minor environment
  differences were recorded as warnings under the authorized methodology
- No registry cleanup or forced restart was performed

Public result: `public_results/rc1_baseline_20260809.jsonl`

Finalization: completed after 39 / 39 accounting and integrity checks

Retention: UNASSESSED
