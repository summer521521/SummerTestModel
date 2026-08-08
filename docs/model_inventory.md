# Current Ollama Model Inventory

Collected via `/api/tags` and `/api/show`; total 44, local 39, cloud 5.

| Model | Digest | Size GiB | Params | Quant | Context | Capabilities | Role hint |
| --- | --- | ---: | --- | --- | ---: | --- | --- |
| `deepscaler:1.5b` | `0031bcf7459f` | 3.316 | 1.8B | F16 | 131072 | completion, thinking, tools | reasoning_name_hint |
| `deepseek-ocr:latest` | `0e7b018b8a22` | 6.228 | 3.3B | F16 | 8192 | completion, vision | ocr |
| `deepseek-r1:8b` | `6995872bfe4c` | 4.867 | 8.2B | Q4_K_M | 131072 | completion, thinking, tools | reasoning_name_hint |
| `devstral-2:123b-cloud` | `d37aca5b6a27` | 0.0 | 123000000000 | fp8 | - | - | general_or_unknown |
| `functiongemma:270m` | `7c19b650567a` | 0.28 | 268.10M | Q8_0 | 32768 | completion, tools | tools |
| `gemma3n:e4b` | `15cb39fd9394` | 7.029 | 6.9B | Q4_K_M | - | - | general_or_unknown |
| `gemma4:e4b` | `c6eb396dbd59` | 8.948 | 8.0B | Q4_K_M | 131072 | audio, completion, thinking, tools, vision | vision |
| `glm-ocr:latest` | `6effedd0dc8a` | 2.067 | 1.1B | F16 | 131072 | completion, tools, vision | ocr |
| `gpt-oss:120b-cloud` | `569662207105` | 0.0 | 116829156672 | MXFP4 | 131072 | completion, thinking, tools | general_or_unknown |
| `granite4.1-guardian:8b` | `f82c0882cec1` | 6.407 | 8.4B | Q6_K | 131072 | completion, thinking, tools | safety |
| `granite4.1:8b` | `444af1c4b2fe` | 4.981 | 8.8B | Q4_K_M | 131072 | completion, tools | general_or_unknown |
| `granite4:7b-a1b-h` | `566b725534ea` | 3.94 | 6.9B | Q4_K_M | 1048576 | completion, tools | general_or_unknown |
| `hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M` | `b4e09c173a61` | 3.038 | 3.4B | Q4_K_M | 131072 | completion, tools, vision | vision |
| `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | `f1ab988bb6ce` | 4.682 | 8.19B | Q4_K_M | 32768 | completion, thinking, tools | general_or_unknown |
| `hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M` | `7a8fccc56374` | 4.283 | 7.59B | Q4_K_M | 262144 | completion, thinking, tools | general_or_unknown |
| `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | `49c1cb13df5f` | 1.807 | 3.08B | Q4_K_M | 65536 | completion, thinking, tools | general_or_unknown |
| `huggingface.co/llmware/phi-4-mini-gguf:latest` | `812893abf9e4` | 2.321 | 3.84B | Q4_K_M | 131072 | completion, tools | general_or_unknown |
| `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | `1a41a532bd9a` | 4.682 | 8.19B | Q4_K_M | 131072 | completion, thinking, tools | reasoning_name_hint |
| `kaelri/hy-mt2:7b-q4_K_M` | `1981e6ac165f` | 4.307 | 7.5B | Q4_K_M | 262144 | completion | translation_name_hint |
| `lfm2.5:8b` | `9cf756159fc2` | 4.802 | 8.5B | Q4_K_M | 128000 | completion, thinking, tools | general_or_unknown |
| `llama3.2:3b` | `a80c4f17acd5` | 1.881 | 3.2B | Q4_K_M | 131072 | completion, tools | general_or_unknown |
| `medgemma1.5:4b` | `433252621ab1` | 3.11 | 4.3B | Q4_K_M | 131072 | completion, vision | vision |
| `minicpm-v4.6:latest` | `e95583acac77` | 1.525 | 752.16M | Q4_K_M | 262144 | completion, thinking, tools, vision | vision |
| `minimax-m3:cloud` | `d03a959f45c0` | 0.0 | 0 | - | 524288 | completion, thinking, tools, vision | vision |
| `ministral-3:8b` | `1922accd5827` | 5.609 | 8.9B | Q4_K_M | 262144 | completion, tools, vision | vision |
| `mistral:7b` | `6577803aa9a0` | 4.073 | 7.2B | Q4_K_M | 32768 | completion, tools | general_or_unknown |
| `nemotron-3-nano:4b` | `6cc467f05439` | 2.643 | 4.0B | Q4_K_M | 262144 | completion, thinking, tools | general_or_unknown |
| `olmo-3:7b-instruct` | `ea72df8c85d7` | 4.165 | 7.3B | Q4_K_M | 65536 | completion, tools | general_or_unknown |
| `olmo-3:7b-think` | `b8d4c92ac9c1` | 4.165 | 7.3B | Q4_K_M | 65536 | completion, thinking | reasoning_name_hint |
| `openbmb/minicpm5:Q4_K_M` | `08239e8f70e0` | 0.641 | 1.1B | Q4_K_M | 131072 | completion, thinking, tools | general_or_unknown |
| `ornith:9b` | `a75697c14589` | 5.243 | 9.0B | Q4_K_M | 262144 | completion, thinking, tools | general_or_unknown |
| `phi4-mini-reasoning:latest` | `3ca8c2865ce9` | 2.936 | 3.8B | Q4_K_M | 131072 | completion, tools | reasoning_name_hint |
| `phi4-mini:latest` | `78fad5d182a7` | 2.321 | 3.8B | Q4_K_M | 131072 | completion, tools | general_or_unknown |
| `qwen3-coder-next:cloud` | `aa626c11ae8d` | 0.0 | 80B | FP8 | - | - | code_name_hint |
| `qwen3-coder:480b-cloud` | `e30e45586389` | 0.0 | 480B | BF16 | - | - | code_name_hint |
| `qwen3-embedding:latest` | `64b933495768` | 4.356 | 7.6B | Q4_K_M | 40960 | embedding, tools | embedding |
| `qwen3-vl:8b` | `901cae732162` | 5.719 | 8.8B | Q4_K_M | 262144 | completion, thinking, tools, vision | vision |
| `qwen3.5:4b` | `2a654d98e6fb` | 3.157 | 4.7B | Q4_K_M | 262144 | completion, thinking, tools, vision | vision |
| `qwen3.5:9b` | `6488c96fa5fa` | 6.142 | 9.7B | Q4_K_M | 262144 | completion, thinking, tools, vision | vision |
| `rnj-1:latest` | `d20e29ab8d0f` | 4.763 | 8.3B | Q4_K_M | 32768 | completion, tools | general_or_unknown |
| `shieldgemma:2b` | `5aad5044d142` | 1.591 | 2.6B | Q4_K_M | 8192 | completion | safety |
| `smollm2:1.7b` | `cef4a1e09247` | 1.695 | 1.7B | Q8_0 | 8192 | completion, tools | general_or_unknown |
| `starcoder2:7b` | `1550ab21b10d` | 3.765 | 7B | Q4_0 | 16384 | completion, insert | code_name_hint |
| `translategemma:latest` | `c49d986b0764` | 3.072 | 4.3B | Q4_K_M | 131072 | completion, vision | vision |
