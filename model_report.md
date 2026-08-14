# SummerTestModel Benchmark 1.0-rc1 Practical Model Report

[English] · [简体中文](model_report.zh-CN.md) · [Complete phase report](docs/final_report.en.md) · [Interactive website](https://summertestmodel-benchmark.walker-ethan.chatgpt.site)

## Scope

This report covers the current practical snapshot built on the normalized baseline:

- 39/39 selected local models completed;
- 1,938 task records and 1,938 immutable private raw files;
- benchmark version `1.0-rc1`;
- strict publication scorer `1.0-rc1.1` and practical scorer `practical-regrade-1`;
- 50 targeted recovery attempts across eight models, with 39 selected into the practical view;
- no missing raw, duplicate inference keys, unresolved scoring errors, or infrastructure-incomplete task records.

The original strict baseline is unchanged. Practical scores come from offline regrading plus explicitly marked selected recovery evidence. They describe local usability on the recorded Windows/Ollama machine, not a universal ranking or a publisher-benchmark equivalent.

## Local results by track

| Track | Leading observed model | RC1 within-track mean | Notes |
| --- | --- | ---: | --- |
| Core | Gemma4, Qwen3-8B Q4, Falcon H1R, Ministral3, Qwen3-VL, Qwen3.5 9B | 0.879 | six-way tie |
| Reasoning | 13 models | 0.800 | current fixtures do not separate the top group |
| Code | `olmo-3:7b-think` | 0.900 | 8/8 completed |
| Translation | `gemma4:e4b`, Qwen3-8B Q4, `qwen3-vl:8b` | 1.000 | tied leaders |
| Tools | Qwen3-8B Q4, `lfm2.5:8b`, `minicpm-v4.6`, `qwen3-vl:8b` | 0.909 | tied leaders |
| Long context | 23 models | 1.000 | only four fixtures; low discrimination |
| Embedding | `qwen3-embedding:latest` | 1.000 | specialist track |
| Safety | `granite4.1-guardian:8b` | 1.000 | specialist track |
| Medical | Nemotron 4B, Qwen3.5 4B, Qwen3.5 9B | 0.800 | application track; not clinical validation |
| OCR | `deepseek-ocr:latest` | 0.792 | 100% completion; GLM-OCR semantic 0.810 but 0% completion |
| Vision | `qwen3-vl:8b` | 1.000 | experimental, eight fixtures |

Complete practical model-by-track rows are available in [public_results/rc1_practical_track_scores.csv](public_results/rc1_practical_track_scores.csv), with the strict table retained in [public_results/rc1_track_scores.csv](public_results/rc1_track_scores.csv). Performance telemetry is separate and adds no capability points.

## Runtime and scoring outcomes

- targeted recovery: 50/50 accounted, 39 selected;
- selected practical snapshot: 5 absolute timeouts and 74 truncation-related records;
- six recovered capability items still lack a scoreable final;
- 0 unresolved scoring errors and 0 infrastructure-incomplete records.

Three `CORE_PRACT_04` scorer crashes were corrected in scorer `1.0-rc1.1`. The practical regrade also separates semantic, protocol, completion, repetition, tool dimensions, and safety confusion metrics. Detailed classifications are in [docs/rc1_failure_analysis.md](docs/rc1_failure_analysis.md), and the 50-item comparison is public in [public_results/rc1_practical_recovery_20260813.csv](public_results/rc1_practical_recovery_20260813.csv).

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
