# SummerTestModel V2 Stable Snapshot

## 发布范围

- 本报告是现有 raw evidence 的离线收口，不恢复中断的模型运行，也不新增模型或题目。
- 当前 comprehensive run 为部分覆盖的稳定快照；它不构成全模型统一排名。
- 原始 `results.jsonl` 与 `raw/` 未被改写。

## 运行摘要

- Run ID：`20260731_v2_comprehensive`
- Task version：`20260731.v2`；publication scorer：`v2.2.0-offline`。
- 派生输入：`offline_regrade.jsonl`；规范化记录 1567 条；原始尝试记录 1974 条。
- 模型清单：44 个（本地 39，cloud 5）；实际有记录模型 33 个。
- 可评分记录：1246 条；基础设施失败：263 条。
- 状态计数：{"network_error": 235, "runtime_error": 56, "syntax_error": 39, "completed": 1098, "timeout_absolute": 19, "truncated": 66, "server_error": 9, "truncated_before_final_answer": 16, "invalid_response": 5, "truncated_repetition": 5, "unsafe_code_detected": 8, "empty_response": 9, "policy_rejected": 2}。
- 能力得分分母只包含有离线评分的记录；network/server/timeout 等基础设施失败不计为能力 0 分。
- 公共核心、规划和专项赛道分别排名，不将不同满分相加。
- 截断、重复退化、策略拒绝与传输失败分别保留，不归因成知识错误。

## 公共核心（不含规划）榜

| 排名 | 模型 | profile | score | coverage | completed | 平均秒 |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1 | `hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M` | `v2_deterministic` | 247/310 | 100.0% | 31/31 | 19.303 |
| 2 | `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | `v2_deterministic` | 225/310 | 100.0% | 31/31 | 18.294 |
| 3 | `nemotron-3-nano:4b` | `v2_deterministic` | 221/310 | 100.0% | 31/31 | 4.104 |

## 规划榜

| 排名 | 模型 | profile | score | coverage | completed | 平均秒 |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1 | `olmo-3:7b-instruct` | `v2_deterministic` | 20/40 | 100.0% | 4/4 | 68.528 |
| 2 | `lfm2.5:8b` | `v2_deterministic` | 10/40 | 100.0% | 4/4 | 12.712 |
| 3 | `granite4:7b-a1b-h` | `v2_deterministic` | 0/40 | 100.0% | 4/4 | 2.112 |
| 4 | `llama3.2:3b` | `v2_deterministic` | 0/40 | 100.0% | 4/4 | 4.531 |
| 5 | `kaelri/hy-mt2:7b-q4_K_M` | `v2_deterministic` | 0/40 | 100.0% | 4/4 | 5.334 |
| 6 | `huggingface.co/llmware/phi-4-mini-gguf:latest` | `v2_deterministic` | 0/40 | 100.0% | 4/4 | 6.228 |
| 7 | `phi4-mini:latest` | `v2_deterministic` | 0/40 | 100.0% | 4/4 | 8.909 |
| 8 | `mistral:7b` | `v2_deterministic` | 0/40 | 100.0% | 4/4 | 9.046 |
| 9 | `smollm2:1.7b` | `v2_deterministic` | 0/40 | 100.0% | 4/4 | 11.206 |
| 10 | `openbmb/minicpm5:Q4_K_M` | `v2_deterministic` | 0/40 | 100.0% | 4/4 | 13.084 |

## 推理扩展榜

| 排名 | 模型 | profile | score | coverage | completed | 平均秒 |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1 | `olmo-3:7b-think` | `reasoning_native` | 70/70 | 70.0% | 7/10 | 474.378 |
| 2 | `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | `reasoning_native` | 10/10 | 10.0% | 1/10 | 11.161 |
| 3 | `nemotron-3-nano:4b` | `reasoning_native` | 90/100 | 100.0% | 10/10 | 9.683 |

## 代码榜

| 排名 | 模型 | profile | score | coverage | completed | 平均秒 |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1 | `olmo-3:7b-think` | `v2_deterministic` | 23.333333333333332/40 | 40.0% | 4/10 | 189.436 |
| 2 | `huggingface.co/llmware/phi-4-mini-gguf:latest` | `v2_deterministic` | 43.333333333333336/80 | 60.0% | 6/10 | 2.208 |
| 3 | `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | `v2_deterministic` | 23.333333333333332/50 | 40.0% | 4/10 | 30.061 |

## 翻译榜

| 排名 | 模型 | profile | score | coverage | completed | 平均秒 |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1 | `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | `v2_deterministic` | 80/80 | 100.0% | 8/8 | 13.344 |
| 2 | `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | `v2_deterministic` | 80/80 | 100.0% | 8/8 | 19.047 |
| 3 | `hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M` | `v2_deterministic` | 78/80 | 100.0% | 8/8 | 15.446 |

## 长上下文榜

| 排名 | 模型 | profile | score | coverage | completed | 平均秒 |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| - | 无适用终态 | - | - | 0 | 0 | - |

## 视觉榜

| 排名 | 模型 | profile | score | coverage | completed | 平均秒 |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1 | `qwen3.5:9b` | `v2_deterministic` | 3.8/5 | 100.0% | 5/5 | 15.879 |
| 2 | `minicpm-v4.6:latest` | `v2_deterministic` | 3.4667/5 | 100.0% | 5/5 | 5.058 |
| 3 | `hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M` | `v2_deterministic` | 3.2666/5 | 100.0% | 5/5 | 5.035 |

## OCR 语义（完成率单列）榜

| 排名 | 模型 | profile | score | coverage | completed | 平均秒 |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1 | `glm-ocr:latest` | `v2_deterministic` | 3.8/5 | 0.0% | 0/5 | 30.228 |
| 2 | `deepseek-ocr:latest` | `v2_deterministic` | 0.0/5 | 100.0% | 5/5 | 10.573 |

## 安全榜

| 排名 | 模型 | profile | score | coverage | completed | 平均秒 |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1 | `granite4.1-guardian:8b` | `v2_deterministic` | 4/4 | 100.0% | 4/4 | 27.047 |
| 2 | `shieldgemma:2b` | `v2_deterministic` | 3/4 | 100.0% | 4/4 | 3.468 |

## 工具榜

| 排名 | 模型 | profile | score | coverage | completed | 平均秒 |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1 | `functiongemma:270m` | `v2_deterministic` | 3/8 | 37.5% | 3/8 | 0.0 |

## Embedding榜

| 排名 | 模型 | profile | score | coverage | completed | 平均秒 |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| - | 无适用终态 | - | - | 0 | 0 | - |

## 稳定性榜

| 排名 | 模型 | profile | score | coverage | completed | 平均秒 |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| - | 无适用终态 | - | - | 0 | 0 | - |

## 失败与人工复核

- failures.csv：403 条，其中基础设施类别见 `infrastructure_failure` 字段。
- manual_review_queue.csv：108 条。
- `offline_regrade.csv` 同时保留 legacy 与 publication 派生状态/分数，可逐条追溯。
- 完整请求、thinking、最终回答、Ollama 性能字段和 raw hash 保存在 JSONL/raw。

## 已知限制

- stage3-recovery-2 在 Ollama `WinError 10061` 后停止；未自动恢复，以免将基础设施故障伪装成新能力数据。
- 后续 comprehensive 专项、医疗、性能和 cloud 阶段未完成，相关赛道仅在已有数据足够时展示。
- OCR 同时报出文本语义、重复退化和截断；不得把截断重复输出解释为完美 OCR。

## 可复现

- Runner：`benchmark_20260629/scripts/benchmark_v2.py`。
- 离线重评分：`benchmark_20260629/scripts/regrade_v2_offline.py`；原始回答不变。
- 任务与评分器版本见 `task_manifest.json`、`scorer_manifest.json`、`offline_regrade_summary.json`。
- 同一 `--run-dir` 重跑对应 stage 会跳过已有终态主键；本快照不要求恢复中断运行。
