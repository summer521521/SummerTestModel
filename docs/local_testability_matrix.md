# Local Testability Matrix

Labels estimate execution feasibility from installed size, RAM, VRAM, API metadata, and historical evidence. They are not model-quality or inclusion decisions.

| Model | Status | Basis |
| --- | --- | --- |
| `deepscaler:1.5b` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `deepseek-ocr:latest` | TESTABLE_WITH_CPU_OFFLOAD | Model exceeds conservative VRAM fit but is small relative to system RAM. |
| `deepseek-r1:8b` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `devstral-2:123b-cloud` | CLOUD_ONLY | Ollama entry is cloud-backed; local model files are not present. |
| `functiongemma:270m` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `gemma3n:e4b` | TESTABLE_WITH_CPU_OFFLOAD | Model exceeds conservative VRAM fit but is small relative to system RAM. |
| `gemma4:e4b` | TESTABLE_BUT_RESOURCE_HEAVY | Model file is large relative to available RAM/VRAM; historical evidence should guide probing. |
| `glm-ocr:latest` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `gpt-oss:120b-cloud` | CLOUD_ONLY | Ollama entry is cloud-backed; local model files are not present. |
| `granite4.1-guardian:8b` | TESTABLE_WITH_CPU_OFFLOAD | Model exceeds conservative VRAM fit but is small relative to system RAM. |
| `granite4.1:8b` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `granite4:7b-a1b-h` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `huggingface.co/llmware/phi-4-mini-gguf:latest` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `kaelri/hy-mt2:7b-q4_K_M` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `lfm2.5:8b` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `llama3.2:3b` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `medgemma1.5:4b` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `minicpm-v4.6:latest` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `minimax-m3:cloud` | CLOUD_ONLY | Ollama entry is cloud-backed; local model files are not present. |
| `ministral-3:8b` | TESTABLE_WITH_CPU_OFFLOAD | Model exceeds conservative VRAM fit but is small relative to system RAM. |
| `mistral:7b` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `nemotron-3-nano:4b` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `olmo-3:7b-instruct` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `olmo-3:7b-think` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `openbmb/minicpm5:Q4_K_M` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `ornith:9b` | TESTABLE_WITH_CPU_OFFLOAD | Model exceeds conservative VRAM fit but is small relative to system RAM. |
| `phi4-mini-reasoning:latest` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `phi4-mini:latest` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `qwen3-coder-next:cloud` | CLOUD_ONLY | Ollama entry is cloud-backed; local model files are not present. |
| `qwen3-coder:480b-cloud` | CLOUD_ONLY | Ollama entry is cloud-backed; local model files are not present. |
| `qwen3-embedding:latest` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `qwen3-vl:8b` | TESTABLE_WITH_CPU_OFFLOAD | Model exceeds conservative VRAM fit but is small relative to system RAM. |
| `qwen3.5:4b` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `qwen3.5:9b` | TESTABLE_WITH_CPU_OFFLOAD | Model exceeds conservative VRAM fit but is small relative to system RAM. |
| `rnj-1:latest` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `shieldgemma:2b` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `smollm2:1.7b` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `starcoder2:7b` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
| `translategemma:latest` | TESTABLE_EXPECTED | Model file size fits a conservative fraction of reported VRAM/RAM. |
