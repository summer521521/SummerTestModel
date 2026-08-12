# Model Benchmark Report

## Benchmark 1.0-rc1 current snapshot

The current formal local baseline covers 39/39 planned models and 1,938 task records. It reports per-track scores only: no general model is promoted by an overall universal total, and specialist models are not penalized for inapplicable tracks. Full results and interpretation are in [docs/rc1_results.md](docs/rc1_results.md).

The strongest observed local results by selected track are:

| Track | Leading observed model | RC1 within-track mean |
| --- | --- | ---: |
| Core | `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | 0.778 |
| Reasoning | `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M`, `hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M`, `lfm2.5:8b` | 0.500 |
| Code | `qwen3-vl:8b` | 0.863 |
| Translation | `gemma4:e4b`, `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | 1.000 |
| Tools | `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M`, `lfm2.5:8b`, `qwen3-vl:8b` | 0.750 |
| OCR (experimental) | `deepseek-ocr:latest` | 0.384 |
| Embedding | `qwen3-embedding:latest` | 1.000 |
| Safety | `granite4.1-guardian:8b` | 1.000 |
| Medical | `nemotron-3-nano:4b` | 0.833 |

These are RC1 fixture scores, not reproductions of publisher benchmarks. See [official claims comparison](docs/official_claims_comparison.md) and [official model references](inventory/official_model_references.csv) for source mapping and comparability limits.

The cloud reference is separate: `gpt-oss:120b-cloud` and `minimax-m3:cloud` completed 142 tasks; three retired provider entries returned HTTP 410. Cloud scores do not affect the 39-model local baseline.

Three legacy scorer crashes were repaired offline in scorer `1.0-rc1.1`; no model response was regenerated. Remaining timeout, truncation, stream, and tool-loop findings are classified in [docs/rc1_failure_analysis.md](docs/rc1_failure_analysis.md).

Retention remains `UNASSESSED`. The report makes no keeper/dominated decision.

## Legacy Experimental Evidence

The remaining sections document the older seven-task/V2 systems. They use different tasks and scorer semantics and are not comparable to Benchmark 1.0-rc1.

### Legacy Executive Summary

- Best overall callable model: `gpt-oss:120b-cloud` at 59/70.
- Best local model: `ornith:9b` at 52/70.
- Best newly added model: `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` at 39/70.
- Local models worth follow-up: `ornith:9b`, `granite4.1:8b`, `deepscaler:1.5b`, `lfm2.5:8b`, `gemma4:e4b`, and `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M`.
- Multi-constraint planning was the hardest category. Most models missed constraints or failed to produce a complete feasible schedule.
- Subscription-gated cloud models were removed from the published results and should be treated as not tested.

### Recommendation Tiers

- Tier 1: `gpt-oss:120b-cloud`, `devstral-2:123b-cloud`, `ornith:9b`.
- Tier 2: `qwen3-coder:480b-cloud`, `qwen3-coder-next:cloud`, `minimax-m3:cloud`, `granite4.1:8b`, `deepscaler:1.5b`, `lfm2.5:8b`, `gemma4:e4b`, `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M`.
- Lightweight usable: `smollm2:1.7b`, `mistral:7b`, `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL`.
- Not recommended for complex agent work in this run: `starcoder2:7b`, `qwen3-vl:8b`, `qwen3.5:9b`, `qwen3.5:4b`, `translategemma:latest`.

### Newly Added Models

| Model | Score | Overall Rank |
| --- | --- | --- |
| `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | 39/70 | 13 |
| `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | 36/70 | 14 |
| `huggingface.co/llmware/phi-4-mini-gguf:latest` | 31/70 | 16 |
| `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | 28/70 | 20 |
| `qwen3.5:4b` | 7/70 | 26 |

### Model Table

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

### Limitations

- Automatic scoring is best for screening and regression tracking, not final human evaluation.
- The code task used a small unit-test harness and does not represent full repository editing ability.
- Cloud model availability depends on account permissions, network state, and service state.

### Incremental Run - 2026-07-30

This independent run did not overwrite the historical table above. Its full evidence package is in [benchmark_20260629/runs/20260730_incremental](benchmark_20260629/runs/20260730_incremental), including raw responses, model digests, machine metadata, status mappings, CSV files and an XLSX workbook.

- Across the safety-verified non-code matrix (60 points), `gemma4:e4b` and `nemotron-3-nano:4b` tied first at 48/60. `gpt-oss:120b-cloud` led callable cloud models with 43/60.
- Across the smaller strict seven-task subset, `deepscaler:1.5b` scored 44/70. This subset excludes model answers deliberately not executed by the safety-gated code evaluator.
- `qwen3-embedding:latest` achieved 6/6 retrieval hits. `qwen3-vl:8b` achieved 2/2 exact visual extractions; Granite Vision and MiniCPM-V extracted the tested contents but not the requested short output format.
- Guardian and ShieldGemma returned labels incompatible with the requested SAFE/UNSAFE schema; they are listed as `invalid_response`, not assigned a safety-accuracy score. Three cloud coder models returned HTTP 410 and are listed as unavailable.

### 20260731_v2_comprehensive

#### V2 Stable Snapshot

本节是基于既有 raw evidence 的离线收口，不恢复中断任务，也不新增模型、题库或全量重测。它与 V1 七题 70 分榜及 20260730 incremental run 独立，三者不能混合排名。

- Task version：`20260731.v2`；publication scorer：`v2.2.0-offline`。
- 运行目录：[V2 comprehensive](benchmark_20260629/runs/20260731_v2_comprehensive/)。
- 清单模型：44（本地 39，cloud 5）；有实际记录模型：33。
- canonical 记录：1567；原始尝试：1974；可评分：1246；基础设施失败：263。
- raw response、`results.jsonl` 和 legacy scores 保持不变；`offline_regrade.csv` 并列保存 legacy 与 publication 派生结果。

#### Comparison Boundaries

- General/Core、Reasoning、Code、Translation、Vision、OCR、Safety、Tools 分别展示；specialist 不进入普通 Core 总榜。
- 仅有可评分记录进入能力得分分母；network/server/timeout/unavailable 不作为能力 0 分。
- coverage 表示该模型在此赛道已有记录的完成比例，不表示整个模型清单覆盖率。OCR 分数为文本语义重叠，重复退化/截断仍由 coverage 和状态单列。long-context、embedding、performance 与 robustness 没有足够 V2 数据时不建立榜单。

#### Existing-data Results

| 赛道 | 第一名 | 得分 | 已有记录 coverage |
| --- | --- | ---: | ---: |
| core | `hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M` | 247/310 | 100.0% |
| reasoning | `olmo-3:7b-think` | 70/70 | 70.0% |
| code | `olmo-3:7b-think` | 23.333333333333332/40 | 40.0% |
| translation | `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | 80/80 | 100.0% |
| long_context | 无适用终态 | - | 0 |
| vision | `qwen3.5:9b` | 3.8/5 | 100.0% |
| ocr | `glm-ocr:latest` | 3.8/5 | 0.0% |
| safety | `granite4.1-guardian:8b` | 4/4 | 100.0% |
| tool | `functiongemma:270m` | 3/8 | 37.5% |
| embedding | 无适用终态 | - | 0 |
| performance | 无适用终态 | - | 0 |
| robustness | 无适用终态 | - | 0 |

完整报告：[final_report.md](benchmark_20260629/runs/20260731_v2_comprehensive/final_report.md)；表格：[all_results.csv](benchmark_20260629/runs/20260731_v2_comprehensive/all_results.csv)、[scores.xlsx](benchmark_20260629/runs/20260731_v2_comprehensive/scores.xlsx)；失败分类：[failures.csv](benchmark_20260629/runs/20260731_v2_comprehensive/failures.csv)。

#### Reproduce and Increment

1. `ollama pull <model>`，再运行 capability reconnaissance；不要以模型名猜测能力。
2. 只对新模型运行适用赛道，使用独立 run directory，并保留 raw response、digest 与状态。
3. 中断后使用同一 run directory resume；终态记录会被跳过，不能覆盖既有有效结果。
4. 使用 `regrade_v2_offline.py` 和 `finalize_v2.py` 从已有 raw 重新生成派生报告。
5. 只有 benchmark major version、scorer 无法离线重评、Ollama 推理行为发生重大变化或用户明确要求时，才考虑全量重测。

V2 使用流式响应、每题持久化、独立任务/评分器版本、受限代码子进程和显式 cloud preflight；截断、策略拒绝、不可用与传输失败不混为能力 0 分。已知限制和未来补测见 [docs/current_project_status.md](docs/current_project_status.md) 与 [docs/future_work.md](docs/future_work.md)。
