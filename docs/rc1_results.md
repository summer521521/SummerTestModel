# SummerTestModel Benchmark 1.0-rc1 Strict Baseline Reference

> This document preserves the original strict scorer view. The current project-facing result is the [practical final report](final_report.en.md), backed by [practical track scores](../public_results/rc1_practical_track_scores.csv) and the [50-item recovery comparison](../public_results/rc1_practical_recovery_20260813.csv). The strict data below has not been overwritten.

## Publication boundary

This snapshot evaluates practical usability on one Windows/Ollama machine. It is not a controlled laboratory comparison. Ollama version, machine profile, quantization, runtime defaults, and run date are recorded as environment metadata rather than fixed cross-era gates.

The 39-model local baseline and the cloud comparison are separate scopes. There is no universal overall score, and specialist tracks are not penalized for inapplicable tasks. Publisher benchmark claims use different prompts, runtimes, precision, datasets, and scoring rules; they are context, not directly comparable RC1 scores.

## Data integrity

- Local baseline: 39/39 models, 1,938 derived records, 1,938 immutable raw files, no missing raw, no duplicate inference key.
- Offline scorer release: `1.0-rc1.1`; repaired three scorer crashes without changing model output.
- Cloud reference: 2 models tested for 142 tasks; 3 provider-retired entries retained as HTTP 410 availability evidence.
- Infrastructure failures are excluded from capability denominators; none occurred in the completed local or cloud task records.

## Local track leaders

Scores below are within-track means only. Vision and OCR are experimental because the small fixture set and strict scoring produce low absolute values.

| Track | Rank | Model | Mean | Scored | Records |
| --- | --- | --- | --- | --- | --- |
| code | 1 | qwen3-vl:8b | 0.8625 | 8 | 8 |
| code | 2 | ornith:9b | 0.7625 | 8 | 8 |
| code | 3 | deepseek-r1:8b | 0.75 | 8 | 8 |
| core | 1 | hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M | 0.777778 | 24 | 24 |
| core | 2 | gemma4:e4b | 0.736111 | 24 | 24 |
| core | 3 | qwen3.5:9b | 0.694444 | 24 | 24 |
| embedding | 1 | qwen3-embedding:latest | 1.0 | 12 | 12 |
| long_context | 1 | gemma4:e4b | 0.5 | 4 | 4 |
| long_context | 2 | qwen3.5:9b | 0.5 | 4 | 4 |
| long_context | 3 | deepseek-r1:8b | 0.25 | 4 | 4 |
| medical | 1 | nemotron-3-nano:4b | 0.833333 | 6 | 6 |
| medical | 2 | hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M | 0.666667 | 6 | 6 |
| medical | 3 | qwen3.5:9b | 0.666667 | 6 | 6 |
| ocr | 1 | deepseek-ocr:latest | 0.384059 | 10 | 10 |
| ocr | 2 | hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M | 0.1 | 10 | 10 |
| ocr | 3 | qwen3-vl:8b | 0.1 | 10 | 10 |
| reasoning | 1 | hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M | 0.5 | 10 | 10 |
| reasoning | 2 | hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M | 0.5 | 10 | 10 |
| reasoning | 3 | lfm2.5:8b | 0.5 | 10 | 10 |
| safety | 1 | granite4.1-guardian:8b | 1.0 | 20 | 20 |
| safety | 2 | shieldgemma:2b | 0.75 | 20 | 20 |
| tools | 1 | hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M | 0.75 | 8 | 8 |
| tools | 2 | lfm2.5:8b | 0.75 | 8 | 8 |
| tools | 3 | qwen3-vl:8b | 0.75 | 8 | 8 |
| translation | 1 | gemma4:e4b | 1.0 | 6 | 6 |
| translation | 2 | hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M | 1.0 | 6 | 6 |
| translation | 3 | granite4.1:8b | 0.966667 | 6 | 6 |
| vision | 1 | gemma4:e4b | 0.125 | 8 | 8 |
| vision | 2 | hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M | 0.125 | 8 | 8 |
| vision | 3 | ministral-3:8b | 0.125 | 8 | 8 |

## Cloud reference

Cloud results do not enter the local baseline or retention decisions.

| Track | Rank | Model | Mean | Records |
| --- | --- | --- | --- | --- |
| code | 1 | minimax-m3:cloud | 0.75 | 8 |
| code | 2 | gpt-oss:120b-cloud | 0.25 | 8 |
| core | 1 | gpt-oss:120b-cloud | 0.652778 | 24 |
| core | 2 | minimax-m3:cloud | 0.611111 | 24 |
| long_context | 1 | gpt-oss:120b-cloud | 0.25 | 4 |
| long_context | 2 | minimax-m3:cloud | 0.25 | 4 |
| ocr | 1 | minimax-m3:cloud | 0.0 | 10 |
| reasoning | 1 | gpt-oss:120b-cloud | 0.5 | 10 |
| reasoning | 2 | minimax-m3:cloud | 0.3 | 10 |
| tools | 1 | minimax-m3:cloud | 0.75 | 8 |
| tools | 2 | gpt-oss:120b-cloud | 0.5 | 8 |
| translation | 1 | gpt-oss:120b-cloud | 0.9 | 6 |
| translation | 2 | minimax-m3:cloud | 0.85 | 6 |
| vision | 1 | minimax-m3:cloud | 0.25 | 8 |

## Performance telemetry

Performance telemetry is descriptive and adds no capability points. Cloud endpoints do not expose comparable server-side eval duration, so local output tokens/s and cloud wall time must not be mixed into one speed leaderboard.

See `public_results/rc1_performance.csv` for per-model fields.

## Known limitations

- The RC1 task set is compact and some tracks are experimental.
- Model quantization, chat template, thinking defaults, and Ollama/runtime behavior materially affect observed results.
- `truncated_before_final` means the budget ended before a distinct final answer; it is not an infrastructure outage.
- Publisher claims are not reproduced unless the exact official benchmark, precision, prompt, and runtime are separately implemented.
- Retention remains `UNASSESSED`; this report does not declare models dominated or delete them.
