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
| 1 | `gpt-oss:120b-cloud` | 59/70 | 84.3% | 0 | 6.09 |
| 2 | `devstral-2:123b-cloud` | 52/70 | 74.3% | 0 | 8.98 |
| 3 | `ornith:9b` | 52/70 | 74.3% | 0 | 36.17 |
| 4 | `qwen3-coder:480b-cloud` | 48/70 | 68.6% | 0 | 3.52 |
| 5 | `qwen3-coder-next:cloud` | 47/70 | 67.1% | 0 | 2.94 |
| 6 | `minimax-m3:cloud` | 47/70 | 67.1% | 0 | 5.63 |
| 7 | `granite4.1:8b` | 45/70 | 64.3% | 0 | 35.1 |
| 8 | `deepscaler:1.5b` | 44/70 | 62.9% | 0 | 17.77 |
| 9 | `lfm2.5:8b` | 41/70 | 58.6% | 0 | 8.96 |
| 10 | `gemma4:e4b` | 40/70 | 57.1% | 0 | 17.83 |
| 11 | `smollm2:1.7b` | 39/70 | 55.7% | 0 | 2.91 |
| 12 | `mistral:7b` | 39/70 | 55.7% | 0 | 11.53 |
| 13 | `phi4-mini-reasoning:latest` | 32/70 | 45.7% | 0 | 57.55 |
| 14 | `phi4-mini:latest` | 30/70 | 42.9% | 0 | 13.73 |
| 15 | `kaelri/hy-mt2:7b-q4_K_M` | 28/70 | 40.0% | 0 | 8.07 |
| 16 | `llama3.2:3b` | 28/70 | 40.0% | 0 | 9.87 |
| 17 | `translategemma:latest` | 21/70 | 30.0% | 0 | 5.91 |
| 18 | `deepseek-r1:8b` | 21/70 | 30.0% | 0 | 90.61 |
| 19 | `qwen3.5:9b` | 17/70 | 24.3% | 0 | 68.57 |
| 20 | `qwen3-vl:8b` | 14/70 | 20.0% | 0 | 104.82 |
| 21 | `starcoder2:7b` | 10/70 | 14.3% | 0 | 18.29 |
| 22 | `qwen3.5:397b-cloud` | 0/70 | 0.0% | 7 | 0.29 |
| 23 | `deepseek-v4-pro:cloud` | 0/70 | 0.0% | 7 | 0.3 |
| 24 | `gemini-3-flash-preview:cloud` | 0/70 | 0.0% | 7 | 0.3 |
| 25 | `glm-5.2:cloud` | 0/70 | 0.0% | 7 | 0.3 |
| 26 | `deepseek-v4-flash:cloud` | 0/70 | 0.0% | 7 | 0.51 |
| 27 | `kimi-k2.7-code:cloud` | 0/70 | 0.0% | 7 | 0.59 |

## 分项结果

### 代码

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `devstral-2:123b-cloud` | code_bugfix | 10/10 | 单元测试全通过 |
| `gpt-oss:120b-cloud` | code_bugfix | 10/10 | 单元测试全通过 |
| `granite4.1:8b` | code_bugfix | 10/10 | 单元测试全通过 |
| `kaelri/hy-mt2:7b-q4_K_M` | code_bugfix | 10/10 | 单元测试全通过 |
| `lfm2.5:8b` | code_bugfix | 10/10 | 单元测试全通过 |
| `minimax-m3:cloud` | code_bugfix | 10/10 | 单元测试全通过 |
| `mistral:7b` | code_bugfix | 10/10 | 单元测试全通过 |
| `ornith:9b` | code_bugfix | 10/10 | 单元测试全通过 |
| `qwen3-coder-next:cloud` | code_bugfix | 10/10 | 单元测试全通过 |
| `qwen3-coder:480b-cloud` | code_bugfix | 10/10 | 单元测试全通过 |
| `qwen3.5:9b` | code_bugfix | 10/10 | 单元测试全通过 |
| `smollm2:1.7b` | code_bugfix | 10/10 | 单元测试全通过 |
| `deepscaler:1.5b` | code_bugfix | 4/10 | Traceback (most recent call last):
  File "C:\WINDOWS\TEMP\tmpw4geqp_3\run_code_test.py", line 15, in <module>
    assert got == expected, (text, got, expected)
           ^^^^^^^^^^^^^^^
AssertionError: ('Apple banana apple, BANANA! pear.' |
| `llama3.2:3b` | code_bugfix | 4/10 | Traceback (most recent call last):
  File "C:\WINDOWS\TEMP\tmpsuc361ou\run_code_test.py", line 15, in <module>
    assert got == expected, (text, got, expected)
           ^^^^^^^^^^^^^^^
AssertionError: ('Apple banana apple, BANANA! pear.' |
| `phi4-mini:latest` | code_bugfix | 4/10 | Traceback (most recent call last):
  File "C:\WINDOWS\TEMP\tmpwvmxnltp\run_code_test.py", line 5, in <module>
    exec(CODE, ns)
  File "<string>", line 16, in <module>
  File "<string>", line 5, in top_k_words
AttributeError: 'dict' object |
| `gemma4:e4b` | code_bugfix | 1/10 | 语法错误：unterminated triple-quoted string literal (detected at line 7) |
| `translategemma:latest` | code_bugfix | 1/10 | 语法错误：'[' was never closed |
| `deepseek-r1:8b` | code_bugfix | 0/10 | 没有给出目标函数 |
| `deepseek-v4-flash:cloud` | code_bugfix | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `deepseek-v4-pro:cloud` | code_bugfix | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `gemini-3-flash-preview:cloud` | code_bugfix | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `glm-5.2:cloud` | code_bugfix | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `kimi-k2.7-code:cloud` | code_bugfix | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `phi4-mini-reasoning:latest` | code_bugfix | 0/10 | 没有给出目标函数 |
| `qwen3-vl:8b` | code_bugfix | 0/10 | 没有给出目标函数 |
| `qwen3.5:397b-cloud` | code_bugfix | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `starcoder2:7b` | code_bugfix | 0/10 | 没有给出目标函数 |

### 可靠性

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `deepscaler:1.5b` | anti_hallucination | 10/10 | 拒绝编造且保留已知信息 |
| `deepseek-r1:8b` | anti_hallucination | 10/10 | 拒绝编造且保留已知信息 |
| `devstral-2:123b-cloud` | anti_hallucination | 10/10 | 拒绝编造且保留已知信息 |
| `gemma4:e4b` | anti_hallucination | 10/10 | 拒绝编造且保留已知信息 |
| `gpt-oss:120b-cloud` | anti_hallucination | 10/10 | 拒绝编造且保留已知信息 |
| `granite4.1:8b` | anti_hallucination | 10/10 | 拒绝编造且保留已知信息 |
| `lfm2.5:8b` | anti_hallucination | 10/10 | 拒绝编造且保留已知信息 |
| `minimax-m3:cloud` | anti_hallucination | 10/10 | 拒绝编造且保留已知信息 |
| `mistral:7b` | anti_hallucination | 10/10 | 拒绝编造且保留已知信息 |
| `ornith:9b` | anti_hallucination | 10/10 | 拒绝编造且保留已知信息 |
| `phi4-mini-reasoning:latest` | anti_hallucination | 10/10 | 拒绝编造且保留已知信息 |
| `phi4-mini:latest` | anti_hallucination | 10/10 | 拒绝编造且保留已知信息 |
| `qwen3-coder-next:cloud` | anti_hallucination | 10/10 | 拒绝编造且保留已知信息 |
| `qwen3-coder:480b-cloud` | anti_hallucination | 10/10 | 拒绝编造且保留已知信息 |
| `qwen3-vl:8b` | anti_hallucination | 10/10 | 拒绝编造且保留已知信息 |
| `kaelri/hy-mt2:7b-q4_K_M` | anti_hallucination | 8/10 | 没有保留已知事实 |
| `smollm2:1.7b` | anti_hallucination | 8/10 | 没有保留已知事实 |
| `translategemma:latest` | anti_hallucination | 5/10 | 没有承认信息不足 |
| `llama3.2:3b` | anti_hallucination | 3/10 | 没有承认信息不足；没有保留已知事实 |
| `qwen3.5:9b` | anti_hallucination | 3/10 | 没有承认信息不足；没有保留已知事实 |
| `starcoder2:7b` | anti_hallucination | 3/10 | 没有承认信息不足；没有保留已知事实 |
| `deepseek-v4-flash:cloud` | anti_hallucination | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `deepseek-v4-pro:cloud` | anti_hallucination | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `gemini-3-flash-preview:cloud` | anti_hallucination | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `glm-5.2:cloud` | anti_hallucination | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `kimi-k2.7-code:cloud` | anti_hallucination | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `qwen3.5:397b-cloud` | anti_hallucination | 0/10 | HTTPError: HTTP Error 403: Forbidden |

### 推理

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `gpt-oss:120b-cloud` | math_reasoning | 10/10 | 完全正确 |
| `deepscaler:1.5b` | math_reasoning | 5/10 | 次数错 |
| `devstral-2:123b-cloud` | math_reasoning | 5/10 | 次数错 |
| `lfm2.5:8b` | math_reasoning | 5/10 | 次数错 |
| `ornith:9b` | math_reasoning | 5/10 | 次数错 |
| `phi4-mini-reasoning:latest` | math_reasoning | 5/10 | 次数错 |
| `deepseek-r1:8b` | math_reasoning | 0/10 | 时间错；次数错 |
| `deepseek-v4-flash:cloud` | math_reasoning | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `deepseek-v4-pro:cloud` | math_reasoning | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `gemini-3-flash-preview:cloud` | math_reasoning | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `gemma4:e4b` | math_reasoning | 0/10 | 时间错；次数错 |
| `glm-5.2:cloud` | math_reasoning | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `granite4.1:8b` | math_reasoning | 0/10 | 时间错；次数错 |
| `kaelri/hy-mt2:7b-q4_K_M` | math_reasoning | 0/10 | 时间错；次数错 |
| `kimi-k2.7-code:cloud` | math_reasoning | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `llama3.2:3b` | math_reasoning | 0/10 | 时间错；次数错 |
| `minimax-m3:cloud` | math_reasoning | 0/10 | 时间错；次数错 |
| `mistral:7b` | math_reasoning | 0/10 | 时间错；次数错 |
| `phi4-mini:latest` | math_reasoning | 0/10 | 时间错；次数错 |
| `qwen3-coder-next:cloud` | math_reasoning | 0/10 | 时间错；次数错 |
| `qwen3-coder:480b-cloud` | math_reasoning | 0/10 | 时间错；次数错 |
| `qwen3-vl:8b` | math_reasoning | 0/10 | 时间错；次数错 |
| `qwen3.5:397b-cloud` | math_reasoning | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `qwen3.5:9b` | math_reasoning | 0/10 | 时间错；次数错 |
| `smollm2:1.7b` | math_reasoning | 0/10 | 时间错；次数错 |
| `starcoder2:7b` | math_reasoning | 0/10 | 时间错；次数错 |
| `translategemma:latest` | math_reasoning | 0/10 | 时间错；次数错 |

### 格式遵循

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `gemma4:e4b` | format_json | 10/10 | 完全正确 |
| `gpt-oss:120b-cloud` | format_json | 10/10 | 完全正确 |
| `minimax-m3:cloud` | format_json | 10/10 | 完全正确 |
| `ornith:9b` | format_json | 9/10 | JSON 外有额外文本 |
| `deepscaler:1.5b` | format_json | 7/10 | code 错；JSON 外有额外文本 |
| `kaelri/hy-mt2:7b-q4_K_M` | format_json | 5/10 | total 错；code 错 |
| `llama3.2:3b` | format_json | 5/10 | total 错；code 错 |
| `mistral:7b` | format_json | 5/10 | total 错；code 错 |
| `qwen3-coder-next:cloud` | format_json | 5/10 | total 错；code 错 |
| `qwen3-coder:480b-cloud` | format_json | 5/10 | total 错；code 错 |
| `smollm2:1.7b` | format_json | 5/10 | total 错；code 错 |
| `devstral-2:123b-cloud` | format_json | 4/10 | total 错；code 错；JSON 外有额外文本 |
| `granite4.1:8b` | format_json | 4/10 | total 错；code 错；JSON 外有额外文本 |
| `phi4-mini:latest` | format_json | 4/10 | total 错；code 错；JSON 外有额外文本 |
| `translategemma:latest` | format_json | 4/10 | total 错；code 错；JSON 外有额外文本 |
| `deepseek-r1:8b` | format_json | 0/10 | 没有输出可解析 JSON |
| `deepseek-v4-flash:cloud` | format_json | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `deepseek-v4-pro:cloud` | format_json | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `gemini-3-flash-preview:cloud` | format_json | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `glm-5.2:cloud` | format_json | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `kimi-k2.7-code:cloud` | format_json | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `lfm2.5:8b` | format_json | 0/10 | 没有输出可解析 JSON |
| `phi4-mini-reasoning:latest` | format_json | 0/10 | 没有输出可解析 JSON |
| `qwen3-vl:8b` | format_json | 0/10 | 没有输出可解析 JSON |
| `qwen3.5:397b-cloud` | format_json | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `qwen3.5:9b` | format_json | 0/10 | 没有输出可解析 JSON |
| `starcoder2:7b` | format_json | 0/10 | 没有输出可解析 JSON |

### 翻译

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `deepseek-r1:8b` | translation_terms | 9/10 | 租户隔离表达弱 |
| `devstral-2:123b-cloud` | translation_terms | 9/10 | 租户隔离表达弱 |
| `gemma4:e4b` | translation_terms | 9/10 | 租户隔离表达弱 |
| `gpt-oss:120b-cloud` | translation_terms | 9/10 | 租户隔离表达弱 |
| `granite4.1:8b` | translation_terms | 9/10 | 租户隔离表达弱 |
| `llama3.2:3b` | translation_terms | 9/10 | 租户隔离表达弱 |
| `qwen3-coder-next:cloud` | translation_terms | 9/10 | 租户隔离表达弱 |
| `qwen3-coder:480b-cloud` | translation_terms | 9/10 | 租户隔离表达弱 |
| `minimax-m3:cloud` | translation_terms | 8/10 | 租户隔离表达弱；长度异常 |
| `mistral:7b` | translation_terms | 8/10 | 丢失 LoRA；租户隔离表达弱 |
| `ornith:9b` | translation_terms | 8/10 | 租户隔离表达弱；长度异常 |
| `translategemma:latest` | translation_terms | 8/10 | 约束语气不足；租户隔离表达弱 |
| `deepscaler:1.5b` | translation_terms | 7/10 | 仍含中文；租户隔离表达弱 |
| `phi4-mini:latest` | translation_terms | 7/10 | 丢失 p95 latency；租户隔离表达弱；长度异常 |
| `lfm2.5:8b` | translation_terms | 6/10 | 仍含中文；租户隔离表达弱；长度异常 |
| `phi4-mini-reasoning:latest` | translation_terms | 6/10 | 仍含中文；租户隔离表达弱；长度异常 |
| `smollm2:1.7b` | translation_terms | 6/10 | 丢失 tenant_id；约束语气不足；租户隔离表达弱；长度异常 |
| `starcoder2:7b` | translation_terms | 5/10 | 仍含中文；约束语气不足；租户隔离表达弱；长度异常 |
| `kaelri/hy-mt2:7b-q4_K_M` | translation_terms | 2/10 | 丢失 RAG；丢失 KV cache；丢失 LoRA；丢失 p95 latency；丢失 tenant_id；约束语气不足；租户隔离表达弱；长度异常 |
| `qwen3-vl:8b` | translation_terms | 2/10 | 丢失 RAG；丢失 KV cache；丢失 LoRA；丢失 p95 latency；丢失 tenant_id；约束语气不足；租户隔离表达弱；长度异常 |
| `qwen3.5:9b` | translation_terms | 2/10 | 丢失 RAG；丢失 KV cache；丢失 LoRA；丢失 p95 latency；丢失 tenant_id；约束语气不足；租户隔离表达弱；长度异常 |
| `deepseek-v4-flash:cloud` | translation_terms | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `deepseek-v4-pro:cloud` | translation_terms | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `gemini-3-flash-preview:cloud` | translation_terms | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `glm-5.2:cloud` | translation_terms | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `kimi-k2.7-code:cloud` | translation_terms | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `qwen3.5:397b-cloud` | translation_terms | 0/10 | HTTPError: HTTP Error 403: Forbidden |

### 规划

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `devstral-2:123b-cloud` | planning_schedule | 4/10 | 没有明确有解；C 在 D 前不清；12:00-13:00 禁行处理不清 |
| `llama3.2:3b` | planning_schedule | 4/10 | 没有明确有解；C 在 D 前不清；12:00-13:00 禁行处理不清 |
| `qwen3-coder:480b-cloud` | planning_schedule | 4/10 | 没有明确有解；C 在 D 前不清；12:00-13:00 禁行处理不清 |
| `qwen3-coder-next:cloud` | planning_schedule | 3/10 | 没有明确有解；C 在 D 前不清；12:00-13:00 禁行处理不清；F 完成时间不清 |
| `deepscaler:1.5b` | planning_schedule | 2/10 | 没有明确有解；A/恢复安排不清；C 在 D 前不清；12:00-13:00 禁行处理不清 |
| `granite4.1:8b` | planning_schedule | 2/10 | 没有明确有解；A/恢复安排不清；C 在 D 前不清；12:00-13:00 禁行处理不清 |
| `lfm2.5:8b` | planning_schedule | 2/10 | 没有明确有解；A/恢复安排不清；C 在 D 前不清；12:00-13:00 禁行处理不清 |
| `mistral:7b` | planning_schedule | 2/10 | 没有明确有解；A/恢复安排不清；C 在 D 前不清；12:00-13:00 禁行处理不清 |
| `phi4-mini-reasoning:latest` | planning_schedule | 2/10 | 没有明确有解；A/恢复安排不清；C 在 D 前不清；12:00-13:00 禁行处理不清 |
| `phi4-mini:latest` | planning_schedule | 2/10 | 没有明确有解；A/恢复安排不清；C 在 D 前不清；12:00-13:00 禁行处理不清 |
| `smollm2:1.7b` | planning_schedule | 2/10 | 没有明确有解；A/恢复安排不清；C 在 D 前不清；12:00-13:00 禁行处理不清 |
| `deepseek-r1:8b` | planning_schedule | 0/10 | 没有明确有解；A/恢复安排不清；C 在 D 前不清；12:00-13:00 禁行处理不清；F 完成时间不清；关键任务缺失 |
| `deepseek-v4-flash:cloud` | planning_schedule | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `deepseek-v4-pro:cloud` | planning_schedule | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `gemini-3-flash-preview:cloud` | planning_schedule | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `gemma4:e4b` | planning_schedule | 0/10 | 没有明确有解；A/恢复安排不清；C 在 D 前不清；12:00-13:00 禁行处理不清；F 完成时间不清；关键任务缺失 |
| `glm-5.2:cloud` | planning_schedule | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `gpt-oss:120b-cloud` | planning_schedule | 0/10 | 没有明确有解；A/恢复安排不清；C 在 D 前不清；12:00-13:00 禁行处理不清；F 完成时间不清；关键任务缺失 |
| `kaelri/hy-mt2:7b-q4_K_M` | planning_schedule | 0/10 | 没有明确有解；A/恢复安排不清；C 在 D 前不清；12:00-13:00 禁行处理不清；F 完成时间不清；关键任务缺失 |
| `kimi-k2.7-code:cloud` | planning_schedule | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `minimax-m3:cloud` | planning_schedule | 0/10 | 没有明确有解；A/恢复安排不清；C 在 D 前不清；12:00-13:00 禁行处理不清；F 完成时间不清；关键任务缺失 |
| `ornith:9b` | planning_schedule | 0/10 | 没有明确有解；A/恢复安排不清；C 在 D 前不清；12:00-13:00 禁行处理不清；F 完成时间不清；关键任务缺失 |
| `qwen3-vl:8b` | planning_schedule | 0/10 | 没有明确有解；A/恢复安排不清；C 在 D 前不清；12:00-13:00 禁行处理不清；F 完成时间不清；关键任务缺失 |
| `qwen3.5:397b-cloud` | planning_schedule | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `qwen3.5:9b` | planning_schedule | 0/10 | 没有明确有解；A/恢复安排不清；C 在 D 前不清；12:00-13:00 禁行处理不清；F 完成时间不清；关键任务缺失 |
| `starcoder2:7b` | planning_schedule | 0/10 | 没有明确有解；A/恢复安排不清；C 在 D 前不清；12:00-13:00 禁行处理不清；F 完成时间不清；关键任务缺失 |
| `translategemma:latest` | planning_schedule | 0/10 | 没有明确有解；A/恢复安排不清；C 在 D 前不清；12:00-13:00 禁行处理不清；F 完成时间不清；关键任务缺失 |

### 长上下文

| 模型 | 测试 | 得分 | 说明 |
| --- | --- | ---: | --- |
| `devstral-2:123b-cloud` | long_context | 10/10 | 正确定位 |
| `gemma4:e4b` | long_context | 10/10 | 正确定位 |
| `gpt-oss:120b-cloud` | long_context | 10/10 | 正确定位 |
| `granite4.1:8b` | long_context | 10/10 | 正确定位 |
| `ornith:9b` | long_context | 10/10 | 正确定位 |
| `qwen3-coder-next:cloud` | long_context | 10/10 | 正确定位 |
| `qwen3-coder:480b-cloud` | long_context | 10/10 | 正确定位 |
| `deepscaler:1.5b` | long_context | 9/10 | 混入干扰项 |
| `minimax-m3:cloud` | long_context | 9/10 | 混入干扰项 |
| `phi4-mini-reasoning:latest` | long_context | 9/10 | 混入干扰项 |
| `lfm2.5:8b` | long_context | 8/10 | 混入干扰项 |
| `smollm2:1.7b` | long_context | 8/10 | 混入干扰项 |
| `mistral:7b` | long_context | 4/10 | 目标项目错 |
| `kaelri/hy-mt2:7b-q4_K_M` | long_context | 3/10 | 目标项目错 |
| `llama3.2:3b` | long_context | 3/10 | 目标项目错 |
| `phi4-mini:latest` | long_context | 3/10 | 目标项目错；混入干扰项 |
| `translategemma:latest` | long_context | 3/10 | 目标项目错 |
| `deepseek-r1:8b` | long_context | 2/10 | 目标项目错 |
| `qwen3-vl:8b` | long_context | 2/10 | 目标项目错 |
| `qwen3.5:9b` | long_context | 2/10 | 目标项目错 |
| `starcoder2:7b` | long_context | 2/10 | 目标项目错 |
| `deepseek-v4-flash:cloud` | long_context | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `deepseek-v4-pro:cloud` | long_context | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `gemini-3-flash-preview:cloud` | long_context | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `glm-5.2:cloud` | long_context | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `kimi-k2.7-code:cloud` | long_context | 0/10 | HTTPError: HTTP Error 403: Forbidden |
| `qwen3.5:397b-cloud` | long_context | 0/10 | HTTPError: HTTP Error 403: Forbidden |

## 模型概览

| 模型 | 类型 | 大小 | 备注 |
| --- | --- | ---: | --- |
| `gpt-oss:120b-cloud` | 云端 | 0.0 GB |  |
| `devstral-2:123b-cloud` | 云端 | 0.0 GB |  |
| `ornith:9b` | 本地 | 5.24 GB |  |
| `qwen3-coder:480b-cloud` | 云端 | 0.0 GB |  |
| `qwen3-coder-next:cloud` | 云端 | 0.0 GB |  |
| `minimax-m3:cloud` | 云端 | 0.0 GB |  |
| `granite4.1:8b` | 本地 | 4.98 GB |  |
| `deepscaler:1.5b` | 本地 | 3.32 GB |  |
| `lfm2.5:8b` | 本地 | 4.8 GB |  |
| `gemma4:e4b` | 本地 | 8.95 GB |  |
| `smollm2:1.7b` | 本地 | 1.7 GB |  |
| `mistral:7b` | 本地 | 4.07 GB |  |
| `phi4-mini-reasoning:latest` | 本地 | 2.94 GB |  |
| `phi4-mini:latest` | 本地 | 2.32 GB |  |
| `kaelri/hy-mt2:7b-q4_K_M` | 本地 | 4.31 GB |  |
| `llama3.2:3b` | 本地 | 1.88 GB |  |
| `translategemma:latest` | 本地 | 3.07 GB |  |
| `deepseek-r1:8b` | 本地 | 4.87 GB |  |
| `qwen3.5:9b` | 本地 | 6.14 GB |  |
| `qwen3-vl:8b` | 本地 | 5.72 GB |  |
| `starcoder2:7b` | 本地 | 3.77 GB |  |
| `qwen3.5:397b-cloud` | 云端 | 0.0 GB |  |
| `deepseek-v4-pro:cloud` | 云端 | 0.0 GB |  |
| `gemini-3-flash-preview:cloud` | 云端 | 0.0 GB |  |
| `glm-5.2:cloud` | 云端 | 0.0 GB |  |
| `deepseek-v4-flash:cloud` | 云端 | 0.0 GB |  |
| `kimi-k2.7-code:cloud` | 云端 | 0.0 GB |  |