# SummerTestModel Benchmark 1.0-rc1 Model Report

[English] · [简体中文](model_report.zh-CN.md) · [Complete phase report](docs/final_report.en.md) · [Interactive website](https://summertestmodel-benchmark.walker-ethan.chatgpt.site)

## Scope

This report covers the current normalized project baseline only:

- 39/39 selected local models completed;
- 1,938 task records and 1,938 immutable private raw files;
- benchmark version `1.0-rc1`;
- publication scorer `1.0-rc1.1`;
- no missing raw, duplicate inference keys, unresolved scoring errors, or infrastructure-incomplete task records.

The results describe practical local usability on the recorded Windows/Ollama machine. They are not a universal model ranking and should not be combined with older project experiments or publisher leaderboard scores.

## Local results by track

| Track | Leading observed model | RC1 within-track mean | Notes |
| --- | --- | ---: | --- |
| Core | `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | 0.778 | 24 scored records |
| Reasoning | `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M`, `hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M`, `lfm2.5:8b` | 0.500 | tied leaders |
| Code | `qwen3-vl:8b` | 0.863 | 8 scored records |
| Translation | `gemma4:e4b`, `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | 1.000 | tied leaders |
| Tools | `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M`, `lfm2.5:8b`, `qwen3-vl:8b` | 0.750 | tied leaders |
| Long context | `gemma4:e4b`, `qwen3.5:9b` | 0.500 | tied leaders |
| Embedding | `qwen3-embedding:latest` | 1.000 | specialist track |
| Safety | `granite4.1-guardian:8b` | 1.000 | specialist track |
| Medical | `nemotron-3-nano:4b` | 0.833 | specialist/application track |
| OCR | `deepseek-ocr:latest` | 0.384 | experimental |
| Vision | `gemma4:e4b`, `hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M`, `ministral-3:8b` | 0.125 | experimental, tied leaders |

Complete model-by-track rows are available in [public_results/rc1_track_scores.csv](public_results/rc1_track_scores.csv). Performance telemetry is reported separately and adds no capability points.

## Runtime and scoring outcomes

- 7 absolute timeouts;
- 104 truncation-related records;
- 19 runtime anomalies;
- 0 unresolved scoring errors after offline regrading;
- 0 infrastructure failures in the completed local task records.

Three `CORE_PRACT_04` scorer crashes were corrected in scorer `1.0-rc1.1`. Existing raw responses were regraded offline; no model inference was repeated for that repair. Detailed classifications are in [docs/rc1_failure_analysis.md](docs/rc1_failure_analysis.md).

## Cloud reference

Cloud evaluation is contextual and does not enter the local baseline. `gpt-oss:120b-cloud` and `minimax-m3:cloud` completed 142 tasks. Three other catalog entries returned provider HTTP 410 and remain availability evidence rather than model capability scores.

## Interpretation boundary

- No universal overall score is calculated.
- Specialist models are evaluated only on applicable tracks.
- Vision and OCR are experimental in this RC1 snapshot.
- Publisher claims are contextual references unless the same dataset, prompt, precision, runtime, and scorer are reproduced.
- Retention remains `UNASSESSED`; this report makes no deletion or dominance decision.

See [the full RC1 report](docs/rc1_results.md), [official-source comparison policy](docs/official_claims_comparison.md), and [official model references](inventory/official_model_references.csv).

## Future incremental evaluations

New models should be added with the existing incremental workflow rather than rerunning all 39 baseline models. Each addition records its digest and runtime, executes only frozen applicable tracks, preserves raw evidence locally, and publishes a sanitized result snapshot. See [docs/INCREMENTAL_MODELS.md](docs/INCREMENTAL_MODELS.md).

## Historical reference

Pre-RC1 V1/V2 results remain archived in the repository for audit only. They are not reproduced in this current report and are not comparable with Benchmark 1.0-rc1. See [docs/legacy_history.md](docs/legacy_history.md).
