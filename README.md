# SummerTestModel

[English] · [简体中文](README.zh-CN.md)

SummerTestModel evaluates interesting and capable small Ollama models on one consumer Windows laptop. The project now starts from a single normalized baseline: **SummerTestModel Benchmark 1.0-rc1**.

> **Start with the complete phase report:** [design, results, all 39 model assessments, recommendations, and limitations](docs/final_report.en.md). The website version is published from the same structured public data.

**Interactive bilingual website:** [summertestmodel-benchmark.walker-ethan.chatgpt.site](https://summertestmodel-benchmark.walker-ethan.chatgpt.site)

## Current practical snapshot

This is the default public view for the project. The original strict RC1 baseline remains immutable; the practical snapshot regrades all existing raw evidence offline and selects only better, scoreable outcomes from one explicitly marked 50-item targeted recovery. Future models will be evaluated incrementally against the same task system.

| Item | Current result |
| --- | --- |
| Local models | 39/39 completed |
| Local task records | 1,938 |
| Private raw evidence | 1,938 files; no missing raw |
| Duplicate inference keys | 0 |
| Unresolved scoring errors | 0 |
| Infrastructure-incomplete records | 0 |
| Benchmark version | `1.0-rc1` |
| Publication scorer | `1.0-rc1.1` |
| Practical scorer | `practical-regrade-1` |
| Targeted recovery | 50 attempted; 39 selected; 6 capability items still lack a scoreable final |
| Ollama runtime snapshots | `0.32.6` strict baseline; `0.32.9` targeted recovery |

The run reflects practical usability on this machine, not a tightly controlled laboratory environment. Runtime and Ollama versions are recorded with each snapshot instead of being permanent compatibility gates.

## Results

There is no universal overall score. General, reasoning, code, translation, tools, vision, OCR, long-context, embedding, safety, medical, and performance results are interpreted within their own tracks. Specialist models are not penalized for tracks that do not apply to them.

Selected local practical leaders below are ranked with completion in view. The complete table retains strict means, practical means, coverage, completion, and recovery counts.

| Track | Leading observed model | Mean score |
| --- | --- | ---: |
| Core | Six models tie, including Qwen3-8B Q4, Qwen3-VL, Gemma4, Qwen3.5 9B | 0.879 |
| Reasoning | Thirteen models tie; current fixtures do not separate the top group | 0.800 |
| Code | `olmo-3:7b-think` | 0.900 |
| Translation | `gemma4:e4b`, Qwen3-8B Q4, `qwen3-vl:8b` | 1.000 |
| Tools | Qwen3-8B Q4, `lfm2.5:8b`, `minicpm-v4.6`, `qwen3-vl:8b` | 0.909 |
| Vision | `qwen3-vl:8b` | 1.000 |
| OCR | `deepseek-ocr:latest` | 0.792 with 100% completion |
| Embedding | `qwen3-embedding:latest` | 1.000 |
| Safety | `granite4.1-guardian:8b` | 1.000 |
| Medical | Nemotron 4B, Qwen3.5 4B, Qwen3.5 9B | 0.800 |

Vision and OCR remain experimental because their fixture sets are small and semantic score can diverge sharply from completion. Retention remains `UNASSESSED`; the project does not yet label models as keepers or dominated.

Start here:

- [Complete phase report](docs/final_report.en.md) · [中文版](docs/final_report.zh-CN.md)
- [Interactive bilingual website](https://summertestmodel-benchmark.walker-ethan.chatgpt.site)
- [Full RC1 results report](docs/rc1_results.md)
- [Current model report](model_report.md)
- [Structured 39-model assessments](public_results/rc1_model_assessments.json)
- [Practical track scores](public_results/rc1_practical_track_scores.csv)
- [Targeted recovery comparison](public_results/rc1_practical_recovery_20260813.csv)
- [Strict baseline track scores](public_results/rc1_track_scores.csv)
- [Performance telemetry](public_results/rc1_performance.csv)
- [Failure analysis](docs/rc1_failure_analysis.md)
- [Sanitized local result records](public_results/rc1_baseline_20260809.jsonl)
- [Cloud reference results](public_results/rc1_cloud_comparison_20260812.jsonl)

The cloud reference is separate from the 39-model local baseline. Two cloud models completed 142 tasks; three retired provider entries returned HTTP 410 and are recorded as availability failures, not capability zeroes.

## Test machine

| Component | Recorded environment |
| --- | --- |
| OS | Windows 11 Home China, build 26200 |
| CPU | Intel Core i5-13500HX, 14 cores / 20 threads |
| RAM | 31.8 GiB |
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU, 8 GiB VRAM |
| Python | 3.12.10 |
| Ollama | 0.32.6 for strict baseline; 0.32.9 for targeted recovery |

See [machine profile](docs/machine_profile.md) and [runtime policy](docs/ollama_runtime_policy.md) for details.

## Add a model later

Adding one model does not require rerunning the 39-model baseline. The incremental workflow records the installed digest, uses an explicitly selected existing capability assignment, runs only applicable frozen tracks, checkpoints every task, and exports a new sanitized result.

```powershell
python scripts/incremental_model.py inspect --model "new-model:tag"
python scripts/incremental_model.py prepare --model "new-model:tag" --reference-model "existing-model:tag"
python scripts/incremental_model.py run --model "new-model:tag" --reference-model "existing-model:tag" --allow-inference
```

See [Incremental model workflow](docs/INCREMENTAL_MODELS.md). The executor does not infer capabilities from a model name and does not invent new tasks or scoring rules.

## Repository structure

```text
config/                    # frozen RC1 manifests, profiles, and policies
inventory/                 # installed model metadata and source mapping
public_results/            # current sanitized RC1 result snapshots
scripts/                   # runner, scorers, validators, and incremental workflow
tests/                     # executor and scorer regression tests
docs/                      # current reports and operating documentation
private_benchmark/         # private benchmark payload; Git ignored
private_runs/              # immutable local raw evidence; Git ignored
benchmark_20260629/        # historical pre-RC1 experiments
legacy_evidence/           # additional historical evidence
```

## Historical reference

Older V1, V2, and incremental experiments remain in [`benchmark_20260629/`](benchmark_20260629/) and [`legacy_evidence/`](legacy_evidence/). They are retained only for historical audit and are not part of the current results or ranking system. See the [brief history index](docs/legacy_history.md).

## Language policy

The project homepage, phase report, and current model report are maintained in English and Simplified Chinese. Machine-readable manifests, schemas, field names, and code remain in English so there is one executable interface; bilingual explanations link to the same underlying artifacts rather than duplicating data.
