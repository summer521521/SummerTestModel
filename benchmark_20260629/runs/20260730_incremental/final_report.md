# 2026-07-30 无人值守增量评测报告

## 本次运行摘要

- Run ID：`20260730_incremental`
- 结构化结果：288 条；核心文本记录：245 条；专用赛道记录：43 条。
- 当前清单中 5 个 cloud 模型已在所有本地阶段完成后执行。
- HTTP 410 的 cloud 记录保留原始 `failed` 证据，并在本报告中归为 `unavailable`，不计作能力 0 分。
- 核心代码题不使用历史 runner 的无约束 `exec`；无法通过 AST 白名单的回答标为 `unsafe_to_execute`，不并入严格 70 分总分。

## 核心文本结果

### 安全可验证的非代码比较（60 分）

| 排名 | 模型 | 非代码分 | 平均秒数 | 状态 |
| ---: | --- | ---: | ---: | --- |
| 1 | `gemma4:e4b` | 48/60 | 18.573 | completed_with_score;unsafe_to_execute |
| 2 | `nemotron-3-nano:4b` | 48/60 | 9.32 | completed_with_score;unsafe_to_execute |
| 3 | `gpt-oss:120b-cloud` | 43/60 | 6.745 | completed_with_score;unsafe_to_execute |
| 4 | `ornith:9b` | 42/60 | 30.435 | completed_with_score;unsafe_to_execute |
| 5 | `deepscaler:1.5b` | 40/60 | 15.968 | completed_with_score |
| 6 | `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | 39/60 | 36.607 | completed_with_score;unsafe_to_execute |
| 7 | `minimax-m3:cloud` | 39/60 | 5.162 | completed_with_score;unsafe_to_execute |
| 8 | `granite4:7b-a1b-h` | 36/60 | 3.748 | completed_with_score;unsafe_to_execute |
| 9 | `granite4.1:8b` | 35/60 | 30.672 | completed_with_score;unsafe_to_execute |
| 10 | `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | 32/60 | 13.793 | completed_with_score |
| 11 | `phi4-mini-reasoning:latest` | 32/60 | 54.421 | completed_with_score |
| 12 | `lfm2.5:8b` | 31/60 | 7.192 | completed_with_score;unsafe_to_execute |
| 13 | `ministral-3:8b` | 31/60 | 27.998 | completed_with_score;unsafe_to_execute |
| 14 | `olmo-3:7b-instruct` | 30/60 | 18.502 | completed_with_score;unsafe_to_execute |
| 15 | `mistral:7b` | 29/60 | 10.547 | completed_with_score;unsafe_to_execute |
| 16 | `smollm2:1.7b` | 29/60 | 2.556 | completed_with_score;unsafe_to_execute |
| 17 | `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | 28/60 | 68.206 | completed_with_score |
| 18 | `openbmb/minicpm5:Q4_K_M` | 27/60 | 6.987 | completed_with_score |
| 19 | `medgemma1.5:4b` | 26/60 | 15.04 | completed_with_score |
| 20 | `phi4-mini:latest` | 26/60 | 10.594 | completed_with_score;unsafe_to_execute |
| 21 | `rnj-1:latest` | 26/60 | 11.864 | completed_with_score;unsafe_to_execute |
| 22 | `gemma3n:e4b` | 24/60 | 7.604 | completed_with_score |
| 23 | `llama3.2:3b` | 24/60 | 8.543 | completed_with_score;unsafe_to_execute |
| 24 | `deepseek-r1:8b` | 21/60 | 81.292 | completed_with_score;unsafe_to_execute |
| 25 | `huggingface.co/llmware/phi-4-mini-gguf:latest` | 21/60 | 11.462 | completed_with_score;unsafe_to_execute |
| 26 | `translategemma:latest` | 20/60 | 3.123 | completed_with_score |
| 27 | `kaelri/hy-mt2:7b-q4_K_M` | 18/60 | 6.476 | completed_with_score;unsafe_to_execute |
| 28 | `olmo-3:7b-think` | 18/60 | 71.057 | completed_with_score;unsafe_to_execute |
| 29 | `hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M` | 13/60 | 56.213 | completed_with_score;unsafe_to_execute |
| 30 | `starcoder2:7b` | 10/60 | 15.01 | completed_with_score |
| 31 | `qwen3.5:4b` | 7/60 | 32.253 | completed_with_score;unsafe_to_execute |
| 32 | `qwen3.5:9b` | 7/60 | 76.881 | completed_with_score;unsafe_to_execute |

### 全 7 题严格可计分结果（70 分）

| 排名 | 模型 | 总分 | 平均秒数 |
| ---: | --- | ---: | ---: |
| 1 | `deepscaler:1.5b` | 44/70 | 15.968 |
| 2 | `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | 33/70 | 13.793 |
| 3 | `phi4-mini-reasoning:latest` | 33/70 | 54.421 |
| 4 | `medgemma1.5:4b` | 30/70 | 15.04 |
| 5 | `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | 29/70 | 68.206 |
| 6 | `openbmb/minicpm5:Q4_K_M` | 28/70 | 6.987 |
| 7 | `gemma3n:e4b` | 25/70 | 7.604 |
| 8 | `translategemma:latest` | 21/70 | 3.123 |
| 9 | `starcoder2:7b` | 11/70 | 15.01 |

## 专用模型结果

### embedding

| 模型 | 项目数 | 可计分正确 | 说明 |
| --- | ---: | ---: | --- |
| `qwen3-embedding:latest` | 6 | 6 | 结构化原始响应见 raw/ |

### ocr

| 模型 | 项目数 | 可计分正确 | 说明 |
| --- | ---: | ---: | --- |
| `deepseek-ocr:latest` | 2 | 0 | 内容正确 0/2；严格格式 0/2 |
| `glm-ocr:latest` | 2 | 2 | 内容正确 2/2；严格格式 0/2 |

### safety

| 模型 | 项目数 | 可计分正确 | 说明 |
| --- | ---: | ---: | --- |
| `granite4.1-guardian:8b` | 12 | 0 | 标签体系不兼容，全部为 invalid_response，不作准确率结论 |
| `shieldgemma:2b` | 12 | 0 | 标签体系不兼容，全部为 invalid_response，不作准确率结论 |

### tool

| 模型 | 项目数 | 可计分正确 | 说明 |
| --- | ---: | ---: | --- |
| `functiongemma:270m` | 3 | 1 | 结构化原始响应见 raw/ |

### vision

| 模型 | 项目数 | 可计分正确 | 说明 |
| --- | ---: | ---: | --- |
| `hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M` | 2 | 2 | 内容正确 2/2；严格格式 0/2 |
| `minicpm-v4.6:latest` | 2 | 2 | 内容正确 2/2；严格格式 0/2 |
| `qwen3-vl:8b` | 2 | 2 | 内容正确 2/2；严格格式 2/2 |

## Cloud 不可用项

| 模型 | 题数 | 原始错误 |
| --- | ---: | --- |
| `devstral-2:123b-cloud` | 7 | HTTPError: HTTP Error 410: Gone |
| `qwen3-coder-next:cloud` | 7 | HTTPError: HTTP Error 410: Gone |
| `qwen3-coder:480b-cloud` | 7 | HTTPError: HTTP Error 410: Gone |

## 可复现说明

- 主 runner：`benchmark_20260629/scripts/incremental_benchmark.py`。
- 恢复方式：以同一 `--run-dir` 重跑对应 `--phase`；已落盘终态不会重测。
- 所有请求及原始响应位于 `raw/`，机器、模型 digest 和运行状态位于同级 JSON 文件。
