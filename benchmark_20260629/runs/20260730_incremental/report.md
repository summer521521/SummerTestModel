# 2026-07-30 增量评测运行报告

- Run ID: `20260730_incremental`
- 核心文本：沿用 2026-06-29 的 7 题、temperature=0、num_predict=900。
- 代码题：本次仅在 AST 白名单与隔离子进程中验证；`unsafe_to_execute` 不计为 0 分。

## 核心文本榜

| 排名 | 模型 | 完成题数 | 有效计分题数 | 总分 | 平均秒数 | 状态 |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `deepscaler:1.5b` | 7 | 7 | 44 / 70 | 15.968 | completed_with_score |
| 2 | `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | 7 | 7 | 33 / 70 | 13.793 | completed_with_score |
| 3 | `phi4-mini-reasoning:latest` | 7 | 7 | 33 / 70 | 54.421 | completed_with_score |
| 4 | `medgemma1.5:4b` | 7 | 7 | 30 / 70 | 15.04 | completed_with_score |
| 5 | `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | 7 | 7 | 29 / 70 | 68.206 | completed_with_score |
| 6 | `openbmb/minicpm5:Q4_K_M` | 7 | 7 | 28 / 70 | 6.987 | completed_with_score |
| 7 | `gemma3n:e4b` | 7 | 7 | 25 / 70 | 7.604 | completed_with_score |
| 8 | `translategemma:latest` | 7 | 7 | 21 / 70 | 3.123 | completed_with_score |
| 9 | `starcoder2:7b` | 7 | 7 | 11 / 70 | 15.01 | completed_with_score |
| - | `deepseek-r1:8b` | 7 | 6 | 未完成 / 70 | 81.292 | completed_with_score;unsafe_to_execute |
| - | `devstral-2:123b-cloud` | 7 | 0 | 未完成 / 70 | 5.505 | failed |
| - | `gemma4:e4b` | 7 | 6 | 未完成 / 70 | 18.573 | completed_with_score;unsafe_to_execute |
| - | `gpt-oss:120b-cloud` | 7 | 6 | 未完成 / 70 | 6.745 | completed_with_score;unsafe_to_execute |
| - | `granite4.1:8b` | 7 | 6 | 未完成 / 70 | 30.672 | completed_with_score;unsafe_to_execute |
| - | `granite4:7b-a1b-h` | 7 | 6 | 未完成 / 70 | 3.748 | completed_with_score;unsafe_to_execute |
| - | `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | 7 | 6 | 未完成 / 70 | 36.607 | completed_with_score;unsafe_to_execute |
| - | `hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M` | 7 | 6 | 未完成 / 70 | 56.213 | completed_with_score;unsafe_to_execute |
| - | `huggingface.co/llmware/phi-4-mini-gguf:latest` | 7 | 6 | 未完成 / 70 | 11.462 | completed_with_score;unsafe_to_execute |
| - | `kaelri/hy-mt2:7b-q4_K_M` | 7 | 6 | 未完成 / 70 | 6.476 | completed_with_score;unsafe_to_execute |
| - | `lfm2.5:8b` | 7 | 6 | 未完成 / 70 | 7.192 | completed_with_score;unsafe_to_execute |
| - | `llama3.2:3b` | 7 | 6 | 未完成 / 70 | 8.543 | completed_with_score;unsafe_to_execute |
| - | `minimax-m3:cloud` | 7 | 6 | 未完成 / 70 | 5.162 | completed_with_score;unsafe_to_execute |
| - | `ministral-3:8b` | 7 | 6 | 未完成 / 70 | 27.998 | completed_with_score;unsafe_to_execute |
| - | `mistral:7b` | 7 | 6 | 未完成 / 70 | 10.547 | completed_with_score;unsafe_to_execute |
| - | `nemotron-3-nano:4b` | 7 | 6 | 未完成 / 70 | 9.32 | completed_with_score;unsafe_to_execute |
| - | `olmo-3:7b-instruct` | 7 | 6 | 未完成 / 70 | 18.502 | completed_with_score;unsafe_to_execute |
| - | `olmo-3:7b-think` | 7 | 6 | 未完成 / 70 | 71.057 | completed_with_score;unsafe_to_execute |
| - | `ornith:9b` | 7 | 6 | 未完成 / 70 | 30.435 | completed_with_score;unsafe_to_execute |
| - | `phi4-mini:latest` | 7 | 6 | 未完成 / 70 | 10.594 | completed_with_score;unsafe_to_execute |
| - | `qwen3-coder-next:cloud` | 7 | 0 | 未完成 / 70 | 5.445 | failed |
| - | `qwen3-coder:480b-cloud` | 7 | 0 | 未完成 / 70 | 5.492 | failed |
| - | `qwen3.5:4b` | 7 | 6 | 未完成 / 70 | 32.253 | completed_with_score;unsafe_to_execute |
| - | `qwen3.5:9b` | 7 | 6 | 未完成 / 70 | 76.881 | completed_with_score;unsafe_to_execute |
| - | `rnj-1:latest` | 7 | 6 | 未完成 / 70 | 11.864 | completed_with_score;unsafe_to_execute |
| - | `smollm2:1.7b` | 7 | 6 | 未完成 / 70 | 2.556 | completed_with_score;unsafe_to_execute |

## 专用赛道

| 赛道 | 模型 | 已记录项目 | 正确项目 |
| --- | --- | ---: | ---: |
| embedding | `qwen3-embedding:latest` | 6 | 6 |
| ocr | `deepseek-ocr:latest` | 2 | 0 |
| ocr | `glm-ocr:latest` | 2 | 0 |
| safety | `granite4.1-guardian:8b` | 12 | 0 |
| safety | `shieldgemma:2b` | 12 | 0 |
| tool | `functiongemma:270m` | 3 | 1 |
| vision | `hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M` | 2 | 0 |
| vision | `minicpm-v4.6:latest` | 2 | 0 |
| vision | `qwen3-vl:8b` | 2 | 2 |
