# Model Capability Matrix

Facts use explicit Ollama metadata where available; `name_hint` is not a capability verdict.

| Model | Explicit capabilities | Role metadata/name hint | Local/cloud | Testability |
| --- | --- | --- | --- | --- |
| `deepscaler:1.5b` | completion, thinking, tools | reasoning_name_hint | local | TESTABLE_EXPECTED |
| `deepseek-ocr:latest` | completion, vision | ocr | local | TESTABLE_WITH_CPU_OFFLOAD |
| `deepseek-r1:8b` | completion, thinking, tools | reasoning_name_hint | local | TESTABLE_EXPECTED |
| `devstral-2:123b-cloud` | - | general_or_unknown | cloud | CLOUD_ONLY |
| `functiongemma:270m` | completion, tools | tools | local | TESTABLE_EXPECTED |
| `gemma3n:e4b` | - | general_or_unknown | local | TESTABLE_WITH_CPU_OFFLOAD |
| `gemma4:e4b` | audio, completion, thinking, tools, vision | vision | local | TESTABLE_BUT_RESOURCE_HEAVY |
| `glm-ocr:latest` | completion, tools, vision | ocr | local | TESTABLE_EXPECTED |
| `gpt-oss:120b-cloud` | completion, thinking, tools | general_or_unknown | cloud | CLOUD_ONLY |
| `granite4.1-guardian:8b` | completion, thinking, tools | safety | local | TESTABLE_WITH_CPU_OFFLOAD |
| `granite4.1:8b` | completion, tools | general_or_unknown | local | TESTABLE_EXPECTED |
| `granite4:7b-a1b-h` | completion, tools | general_or_unknown | local | TESTABLE_EXPECTED |
| `hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M` | completion, tools, vision | vision | local | TESTABLE_EXPECTED |
| `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | completion, thinking, tools | general_or_unknown | local | TESTABLE_EXPECTED |
| `hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M` | completion, thinking, tools | general_or_unknown | local | TESTABLE_EXPECTED |
| `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | completion, thinking, tools | general_or_unknown | local | TESTABLE_EXPECTED |
| `huggingface.co/llmware/phi-4-mini-gguf:latest` | completion, tools | general_or_unknown | local | TESTABLE_EXPECTED |
| `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | completion, thinking, tools | reasoning_name_hint | local | TESTABLE_EXPECTED |
| `kaelri/hy-mt2:7b-q4_K_M` | completion | translation_name_hint | local | TESTABLE_EXPECTED |
| `lfm2.5:8b` | completion, thinking, tools | general_or_unknown | local | TESTABLE_EXPECTED |
| `llama3.2:3b` | completion, tools | general_or_unknown | local | TESTABLE_EXPECTED |
| `medgemma1.5:4b` | completion, vision | vision | local | TESTABLE_EXPECTED |
| `minicpm-v4.6:latest` | completion, thinking, tools, vision | vision | local | TESTABLE_EXPECTED |
| `minimax-m3:cloud` | completion, thinking, tools, vision | vision | cloud | CLOUD_ONLY |
| `ministral-3:8b` | completion, tools, vision | vision | local | TESTABLE_WITH_CPU_OFFLOAD |
| `mistral:7b` | completion, tools | general_or_unknown | local | TESTABLE_EXPECTED |
| `nemotron-3-nano:4b` | completion, thinking, tools | general_or_unknown | local | TESTABLE_EXPECTED |
| `olmo-3:7b-instruct` | completion, tools | general_or_unknown | local | TESTABLE_EXPECTED |
| `olmo-3:7b-think` | completion, thinking | reasoning_name_hint | local | TESTABLE_EXPECTED |
| `openbmb/minicpm5:Q4_K_M` | completion, thinking, tools | general_or_unknown | local | TESTABLE_EXPECTED |
| `ornith:9b` | completion, thinking, tools | general_or_unknown | local | TESTABLE_WITH_CPU_OFFLOAD |
| `phi4-mini-reasoning:latest` | completion, tools | reasoning_name_hint | local | TESTABLE_EXPECTED |
| `phi4-mini:latest` | completion, tools | general_or_unknown | local | TESTABLE_EXPECTED |
| `qwen3-coder-next:cloud` | - | code_name_hint | cloud | CLOUD_ONLY |
| `qwen3-coder:480b-cloud` | - | code_name_hint | cloud | CLOUD_ONLY |
| `qwen3-embedding:latest` | embedding, tools | embedding | local | TESTABLE_EXPECTED |
| `qwen3-vl:8b` | completion, thinking, tools, vision | vision | local | TESTABLE_WITH_CPU_OFFLOAD |
| `qwen3.5:4b` | completion, thinking, tools, vision | vision | local | TESTABLE_EXPECTED |
| `qwen3.5:9b` | completion, thinking, tools, vision | vision | local | TESTABLE_WITH_CPU_OFFLOAD |
| `rnj-1:latest` | completion, tools | general_or_unknown | local | TESTABLE_EXPECTED |
| `shieldgemma:2b` | completion | safety | local | TESTABLE_EXPECTED |
| `smollm2:1.7b` | completion, tools | general_or_unknown | local | TESTABLE_EXPECTED |
| `starcoder2:7b` | completion, insert | code_name_hint | local | TESTABLE_EXPECTED |
| `translategemma:latest` | completion, vision | vision | local | TESTABLE_EXPECTED |
