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
| 1 | `gemini-3-flash-preview:cloud` | 0/70 | 0.0% | 7 | 0.29 |
| 2 | `qwen3.5:397b-cloud` | 0/70 | 0.0% | 7 | 0.29 |
| 3 | `glm-5.2:cloud` | 0/70 | 0.0% | 7 | 0.37 |
| 4 | `deepseek-v4-pro:cloud` | 0/70 | 0.0% | 7 | 0.44 |
| 5 | `kimi-k2.7-code:cloud` | 0/70 | 0.0% | 7 | 0.48 |
| 6 | `deepseek-v4-flash:cloud` | 0/70 | 0.0% | 7 | 0.55 |

## 分项结果

### 代码

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `deepseek-v4-flash:cloud` | code_bugfix | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `deepseek-v4-pro:cloud` | code_bugfix | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `gemini-3-flash-preview:cloud` | code_bugfix | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `glm-5.2:cloud` | code_bugfix | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `kimi-k2.7-code:cloud` | code_bugfix | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `qwen3.5:397b-cloud` | code_bugfix | 0/10 | HTTPError: HTTP Error 403: Forbidden |

### 可靠性

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `deepseek-v4-flash:cloud` | anti_hallucination | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `deepseek-v4-pro:cloud` | anti_hallucination | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `gemini-3-flash-preview:cloud` | anti_hallucination | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `glm-5.2:cloud` | anti_hallucination | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `kimi-k2.7-code:cloud` | anti_hallucination | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `qwen3.5:397b-cloud` | anti_hallucination | 0/10 | HTTPError: HTTP Error 403: Forbidden |

### 推理

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `deepseek-v4-flash:cloud` | math_reasoning | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `deepseek-v4-pro:cloud` | math_reasoning | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `gemini-3-flash-preview:cloud` | math_reasoning | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `glm-5.2:cloud` | math_reasoning | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `kimi-k2.7-code:cloud` | math_reasoning | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `qwen3.5:397b-cloud` | math_reasoning | 0/10 | HTTPError: HTTP Error 403: Forbidden |

### 格式遵循

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `deepseek-v4-flash:cloud` | format_json | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `deepseek-v4-pro:cloud` | format_json | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `gemini-3-flash-preview:cloud` | format_json | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `glm-5.2:cloud` | format_json | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `kimi-k2.7-code:cloud` | format_json | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `qwen3.5:397b-cloud` | format_json | 0/10 | HTTPError: HTTP Error 403: Forbidden |

### 翻译

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `deepseek-v4-flash:cloud` | translation_terms | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `deepseek-v4-pro:cloud` | translation_terms | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `gemini-3-flash-preview:cloud` | translation_terms | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `glm-5.2:cloud` | translation_terms | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `kimi-k2.7-code:cloud` | translation_terms | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `qwen3.5:397b-cloud` | translation_terms | 0/10 | HTTPError: HTTP Error 403: Forbidden |

### 规划

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `deepseek-v4-flash:cloud` | planning_schedule | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `deepseek-v4-pro:cloud` | planning_schedule | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `gemini-3-flash-preview:cloud` | planning_schedule | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `glm-5.2:cloud` | planning_schedule | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `kimi-k2.7-code:cloud` | planning_schedule | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `qwen3.5:397b-cloud` | planning_schedule | 0/10 | HTTPError: HTTP Error 403: Forbidden |

### 长上下文

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `deepseek-v4-flash:cloud` | long_context | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `deepseek-v4-pro:cloud` | long_context | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `gemini-3-flash-preview:cloud` | long_context | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `glm-5.2:cloud` | long_context | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `kimi-k2.7-code:cloud` | long_context | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `qwen3.5:397b-cloud` | long_context | 0/10 | HTTPError: HTTP Error 403: Forbidden |

## 模型概览

| 模型 | 类型 | 大小 | 备注 |
| --- | --- | ---: | --- |
| `gemini-3-flash-preview:cloud` | 云端 | 0.0 GB |  |
| `qwen3.5:397b-cloud` | 云端 | 0.0 GB |  |
| `glm-5.2:cloud` | 云端 | 0.0 GB |  |
| `deepseek-v4-pro:cloud` | 云端 | 0.0 GB |  |
| `kimi-k2.7-code:cloud` | 云端 | 0.0 GB |  |
| `deepseek-v4-flash:cloud` | 云端 | 0.0 GB |  |