# Benchmark 20260629 结果报告

## 测试内容

本批次覆盖格式遵循、数学推理、长上下文检索、技术翻译、抗幻觉、代码修复和多约束规划。每题 10 分，总分 70 分。

## 过程

- 使用 Ollama 本地 API `/api/generate` 调用模型。
- 温度设为 0，限制输出长度为 900 token，尽量减少随机性。
- 每个模型每道题保存原始回答到 `raw/`，再用脚本自动判分。
- `qwen3-embedding` 属于嵌入模型，默认不参与生成式问答评测。

## 总排名

| 排名 | 模型 | 总分 | 百分比 | 失败题数 | 平均耗时(s) |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | 39/70 | 55.7% | 0 | 38.76 |
| 2 | `huggingface.co/llmware/phi-4-mini-gguf:latest` | 31/70 | 44.3% | 0 | 14.67 |
| 3 | `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | 28/70 | 40.0% | 0 | 81.88 |
| 4 | `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | 22/70 | 31.4% | 0 | 15.7 |

## 分项结果

### 代码

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `huggingface.co/llmware/phi-4-mini-gguf:latest` | code_bugfix | 10/10 | 单元测试全通过 |
| `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | code_bugfix | 0/10 | 没有给出目标函数 |
| `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | code_bugfix | 0/10 | 没有给出目标函数 |

### 可靠性

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | anti_hallucination | 10/10 | 拒绝编造且保留已知信息 |
| `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | anti_hallucination | 5/10 | 没有保留已知事实；疑似编造细节 |
| `huggingface.co/llmware/phi-4-mini-gguf:latest` | anti_hallucination | 3/10 | 没有承认信息不足；没有保留已知事实 |

### 推理

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | math_reasoning | 5/10 | 时间错 |
| `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | math_reasoning | 5/10 | 次数错 |
| `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | math_reasoning | 0/10 | 时间错；次数错 |
| `huggingface.co/llmware/phi-4-mini-gguf:latest` | math_reasoning | 0/10 | 时间错；次数错 |

### 格式遵循

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | format_json | 10/10 | 完全正确 |
| `huggingface.co/llmware/phi-4-mini-gguf:latest` | format_json | 5/10 | total 错；code 错 |
| `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | format_json | 2/10 | 字段不全；total 错；code 错；JSON 外有额外文本 |
| `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | format_json | 0/10 | 没有输出可解析 JSON |

### 翻译

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | translation_terms | 9/10 | 租户隔离表达弱 |
| `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | translation_terms | 7/10 | 仍含中文；租户隔离表达弱 |
| `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | translation_terms | 6/10 | 仍含中文；租户隔离表达弱；长度异常 |
| `huggingface.co/llmware/phi-4-mini-gguf:latest` | translation_terms | 6/10 | 丢失 KV cache；丢失 p95 latency；租户隔离表达弱；长度异常 |

### 规划

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `huggingface.co/llmware/phi-4-mini-gguf:latest` | planning_schedule | 4/10 | 没有明确有解；C 在 D 前不清；12:00-13:00 禁行处理不清 |
| `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | planning_schedule | 2/10 | 没有明确有解；A/恢复安排不清；C 在 D 前不清；12:00-13:00 禁行处理不清 |
| `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | planning_schedule | 0/10 | 没有明确有解；A/恢复安排不清；C 在 D 前不清；12:00-13:00 禁行处理不清；F 完成时间不清；关键任务缺失 |

### 长上下文

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | long_context | 10/10 | 正确定位 |
| `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | long_context | 9/10 | 混入干扰项 |
| `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | long_context | 9/10 | 混入干扰项 |
| `huggingface.co/llmware/phi-4-mini-gguf:latest` | long_context | 3/10 | 目标项目错；混入干扰项 |

## 模型概览

| 模型 | 类型 | 大小 | 备注 |
| --- | --- | ---: | --- |
| `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | 本地 | 4.68 GB |  |
| `huggingface.co/llmware/phi-4-mini-gguf:latest` | 本地 | 2.32 GB |  |
| `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | 本地 | 4.68 GB |  |
| `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | 本地 | 1.81 GB |  |