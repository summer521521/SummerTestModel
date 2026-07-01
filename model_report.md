# Model Benchmark Report

## Executive Summary

- Best overall callable model: `gpt-oss:120b-cloud` at 59/70.
- Best local model: `ornith:9b` at 52/70.
- Best newly added model: `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` at 39/70.
- Local models worth follow-up: `ornith:9b`, `granite4.1:8b`, `deepscaler:1.5b`, `lfm2.5:8b`, `gemma4:e4b`, and `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M`.
- Multi-constraint planning was the hardest category. Most models missed constraints or failed to produce a complete feasible schedule.
- Subscription-gated cloud models were removed from the published results and should be treated as not tested.

## Recommendation Tiers

- Tier 1: `gpt-oss:120b-cloud`, `devstral-2:123b-cloud`, `ornith:9b`.
- Tier 2: `qwen3-coder:480b-cloud`, `qwen3-coder-next:cloud`, `minimax-m3:cloud`, `granite4.1:8b`, `deepscaler:1.5b`, `lfm2.5:8b`, `gemma4:e4b`, `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M`.
- Lightweight usable: `smollm2:1.7b`, `mistral:7b`, `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL`.
- Not recommended for complex agent work in this run: `starcoder2:7b`, `qwen3-vl:8b`, `qwen3.5:9b`, `qwen3.5:4b`, `translategemma:latest`.

## Newly Added Models

| Model | Score | Overall Rank |
| --- | --- | --- |
| `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | 39/70 | 13 |
| `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | 36/70 | 14 |
| `huggingface.co/llmware/phi-4-mini-gguf:latest` | 31/70 | 16 |
| `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | 28/70 | 20 |
| `qwen3.5:4b` | 7/70 | 26 |

## Model Table

| Rank | Model | Type | Score | Percent | Errors | Avg seconds |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `gpt-oss:120b-cloud` | Cloud | 59/70 | 84.3% | 0 | 6.09 |
| 2 | `devstral-2:123b-cloud` | Cloud | 52/70 | 74.3% | 0 | 8.98 |
| 3 | `ornith:9b` | Local | 52/70 | 74.3% | 0 | 36.17 |
| 4 | `qwen3-coder:480b-cloud` | Cloud | 48/70 | 68.6% | 0 | 3.52 |
| 5 | `qwen3-coder-next:cloud` | Cloud | 47/70 | 67.1% | 0 | 2.94 |
| 6 | `minimax-m3:cloud` | Cloud | 47/70 | 67.1% | 0 | 5.63 |
| 7 | `granite4.1:8b` | Local | 45/70 | 64.3% | 0 | 35.1 |
| 8 | `deepscaler:1.5b` | Local | 44/70 | 62.9% | 0 | 17.77 |
| 9 | `lfm2.5:8b` | Local | 41/70 | 58.6% | 0 | 8.96 |
| 10 | `gemma4:e4b` | Local | 40/70 | 57.1% | 0 | 17.83 |
| 11 | `smollm2:1.7b` | Local | 39/70 | 55.7% | 0 | 2.91 |
| 12 | `mistral:7b` | Local | 39/70 | 55.7% | 0 | 11.53 |
| 13 | `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | Local | 39/70 | 55.7% | 0 | 38.76 |
| 14 | `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | Local | 36/70 | 51.4% | 0 | 13.81 |
| 15 | `phi4-mini-reasoning:latest` | Local | 32/70 | 45.7% | 0 | 57.55 |
| 16 | `huggingface.co/llmware/phi-4-mini-gguf:latest` | Local | 31/70 | 44.3% | 0 | 14.67 |
| 17 | `phi4-mini:latest` | Local | 30/70 | 42.9% | 0 | 13.73 |
| 18 | `kaelri/hy-mt2:7b-q4_K_M` | Local | 28/70 | 40.0% | 0 | 8.07 |
| 19 | `llama3.2:3b` | Local | 28/70 | 40.0% | 0 | 9.87 |
| 20 | `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | Local | 28/70 | 40.0% | 0 | 81.88 |
| 21 | `translategemma:latest` | Local | 21/70 | 30.0% | 0 | 5.91 |
| 22 | `deepseek-r1:8b` | Local | 21/70 | 30.0% | 0 | 90.61 |
| 23 | `qwen3.5:9b` | Local | 17/70 | 24.3% | 0 | 68.57 |
| 24 | `qwen3-vl:8b` | Local | 14/70 | 20.0% | 0 | 104.82 |
| 25 | `starcoder2:7b` | Local | 10/70 | 14.3% | 0 | 18.29 |
| 26 | `qwen3.5:4b` | Local | 7/70 | 10.0% | 0 | 28.78 |

## Limitations

- Automatic scoring is best for screening and regression tracking, not final human evaluation.
- The code task used a small unit-test harness and does not represent full repository editing ability.
- Cloud model availability depends on account permissions, network state, and service state.
