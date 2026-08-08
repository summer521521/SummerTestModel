# Web GPT Local Preparation Handoff

## Repository

- Branch at audit start: `main`; HEAD `ea684625749aeafd1709f2d8a113cd268aa3db7d`; upstream `origin/main`.
- The tree was clean before preparation. No unpushed commit or important untracked user artifact was found.
- Old benchmark systems are tracked historical evidence. V1 `benchmark.py` has unsafe in-process code execution; V2 has useful persistence but embeds old tasks/scorers.

## Machine

- CPU: 13th Gen Intel(R) Core(TM) i5-13500HX (14C/20T)
- RAM: 31.797 GiB
- GPU: NVIDIA GeForce RTX 4060 Laptop GPU, 8188 MiB VRAM, driver 610.88, compute capability 8.9
- Python: 3.12.10; Ollama: 0.32.6
- Workspace drive free-space data is in `environment/machine_profile.json`.

## Models

- Current inventory: 44 entries; 39 local and 5 cloud.
- Exact digest, size, params, quantization, context, capabilities, metadata confidence, testability and role hints are in `inventory/model_inventory.csv` and `handoff/model_candidates_for_architect.csv`.
- Role hints are facts/name hints, not keeper/dominance decisions.

## Historical Failure Evidence

```json
{
  "network_error": 235,
  "syntax_error": 95,
  "truncated": 94,
  "timeout_absolute": 19,
  "completed": 1076,
  "server_error": 9,
  "truncated_before_final_answer": 25,
  "runtime_error": 12,
  "unsafe_code_detected": 2,
  "policy_rejected": 1,
  "completed_with_score": 244,
  "unsafe_to_execute": 23,
  "failed": 21
}
```

## Timing Evidence

```json
{
  "code": {
    "count": 167,
    "p50_seconds": 6.926,
    "p90_seconds": 149.046,
    "p95_seconds": 172.178,
    "max_seconds": 7222.91
  },
  "core": {
    "count": 841,
    "p50_seconds": 4.937,
    "p90_seconds": 59.387,
    "p95_seconds": 86.626,
    "max_seconds": 237.835
  },
  "core_text": {
    "count": 245,
    "p50_seconds": 11.911,
    "p90_seconds": 68.709,
    "p95_seconds": 87.039,
    "max_seconds": 118.521
  },
  "embedding": {
    "count": 6,
    "p50_seconds": 0.471,
    "p90_seconds": 4.495,
    "p95_seconds": 5.404,
    "max_seconds": 6.313
  },
  "ocr": {
    "count": 14,
    "p50_seconds": 18.69,
    "p90_seconds": 29.724,
    "p95_seconds": 30.678,
    "max_seconds": 32.434
  },
  "reasoning": {
    "count": 131,
    "p50_seconds": 48.236,
    "p90_seconds": 900.023,
    "p95_seconds": 900.067,
    "max_seconds": 900.13
  },
  "safety": {
    "count": 32,
    "p50_seconds": 4.372,
    "p90_seconds": 22.526,
    "p95_seconds": 30.018,
    "max_seconds": 35.179
  },
  "tool": {
    "count": 3,
    "p50_seconds": 4.09,
    "p90_seconds": 34.694,
    "p95_seconds": 38.519,
    "max_seconds": 42.345
  },
  "translation": {
    "count": 139,
    "p50_seconds": 4.314,
    "p90_seconds": 24.803,
    "p95_seconds": 79.838,
    "max_seconds": 23374.043
  },
  "vision": {
    "count": 26,
    "p50_seconds": 10.557,
    "p90_seconds": 53.952,
    "p95_seconds": 66.588,
    "max_seconds": 66.825
  }
}
```

## Infrastructure Readiness

- Historical persistence and raw evidence are preserved.
- New specification-free executor core provides atomic state, fsync JSONL, immutable raw evidence, resume, failure isolation, mock adapter, circuit-breaker placeholders, doctor and status.
- Doctor must return NOT_READY while any architect field is pending.
- No formal inference was run during preparation.

## Decisions Needed From Web GPT

- Benchmark/task/scorer manifests and their versions/hashes.
- Model selection and capability eligibility matrix.
- Generation profiles, context/output limits and keep-alive policy.
- Inactivity/absolute timeout values per profile.
- Retry and circuit-breaker thresholds/waits/recovery limits.
- Scoring semantics, weights, ranking, size classes, dominance and retention rules.
- Final execution plan and release/version policy.


## Per-model Core Facts

| Model | Digest | GiB | Params | Quant | Context | Local/cloud | Capabilities | Role hint | Testability |
| --- | --- | ---: | --- | --- | ---: | --- | --- | --- | --- |
| `deepscaler:1.5b` | `0031bcf7459f` | 3.316 | 1.8B | F16 | 131072 | local | completion, thinking, tools | reasoning_name_hint | TESTABLE_EXPECTED |
| `deepseek-ocr:latest` | `0e7b018b8a22` | 6.228 | 3.3B | F16 | 8192 | local | completion, vision | ocr | TESTABLE_WITH_CPU_OFFLOAD |
| `deepseek-r1:8b` | `6995872bfe4c` | 4.867 | 8.2B | Q4_K_M | 131072 | local | completion, thinking, tools | reasoning_name_hint | TESTABLE_EXPECTED |
| `devstral-2:123b-cloud` | `d37aca5b6a27` | 0.0 | 123000000000 | fp8 | - | cloud | - | general_or_unknown | CLOUD_ONLY |
| `functiongemma:270m` | `7c19b650567a` | 0.28 | 268.10M | Q8_0 | 32768 | local | completion, tools | tools | TESTABLE_EXPECTED |
| `gemma3n:e4b` | `15cb39fd9394` | 7.029 | 6.9B | Q4_K_M | - | local | - | general_or_unknown | TESTABLE_WITH_CPU_OFFLOAD |
| `gemma4:e4b` | `c6eb396dbd59` | 8.948 | 8.0B | Q4_K_M | 131072 | local | audio, completion, thinking, tools, vision | vision | TESTABLE_BUT_RESOURCE_HEAVY |
| `glm-ocr:latest` | `6effedd0dc8a` | 2.067 | 1.1B | F16 | 131072 | local | completion, tools, vision | ocr | TESTABLE_EXPECTED |
| `gpt-oss:120b-cloud` | `569662207105` | 0.0 | 116829156672 | MXFP4 | 131072 | cloud | completion, thinking, tools | general_or_unknown | CLOUD_ONLY |
| `granite4.1-guardian:8b` | `f82c0882cec1` | 6.407 | 8.4B | Q6_K | 131072 | local | completion, thinking, tools | safety | TESTABLE_WITH_CPU_OFFLOAD |
| `granite4.1:8b` | `444af1c4b2fe` | 4.981 | 8.8B | Q4_K_M | 131072 | local | completion, tools | general_or_unknown | TESTABLE_EXPECTED |
| `granite4:7b-a1b-h` | `566b725534ea` | 3.94 | 6.9B | Q4_K_M | 1048576 | local | completion, tools | general_or_unknown | TESTABLE_EXPECTED |
| `hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M` | `b4e09c173a61` | 3.038 | 3.4B | Q4_K_M | 131072 | local | completion, tools, vision | vision | TESTABLE_EXPECTED |
| `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | `f1ab988bb6ce` | 4.682 | 8.19B | Q4_K_M | 32768 | local | completion, thinking, tools | general_or_unknown | TESTABLE_EXPECTED |
| `hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M` | `7a8fccc56374` | 4.283 | 7.59B | Q4_K_M | 262144 | local | completion, thinking, tools | general_or_unknown | TESTABLE_EXPECTED |
| `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | `49c1cb13df5f` | 1.807 | 3.08B | Q4_K_M | 65536 | local | completion, thinking, tools | general_or_unknown | TESTABLE_EXPECTED |
| `huggingface.co/llmware/phi-4-mini-gguf:latest` | `812893abf9e4` | 2.321 | 3.84B | Q4_K_M | 131072 | local | completion, tools | general_or_unknown | TESTABLE_EXPECTED |
| `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | `1a41a532bd9a` | 4.682 | 8.19B | Q4_K_M | 131072 | local | completion, thinking, tools | reasoning_name_hint | TESTABLE_EXPECTED |
| `kaelri/hy-mt2:7b-q4_K_M` | `1981e6ac165f` | 4.307 | 7.5B | Q4_K_M | 262144 | local | completion | translation_name_hint | TESTABLE_EXPECTED |
| `lfm2.5:8b` | `9cf756159fc2` | 4.802 | 8.5B | Q4_K_M | 128000 | local | completion, thinking, tools | general_or_unknown | TESTABLE_EXPECTED |
| `llama3.2:3b` | `a80c4f17acd5` | 1.881 | 3.2B | Q4_K_M | 131072 | local | completion, tools | general_or_unknown | TESTABLE_EXPECTED |
| `medgemma1.5:4b` | `433252621ab1` | 3.11 | 4.3B | Q4_K_M | 131072 | local | completion, vision | vision | TESTABLE_EXPECTED |
| `minicpm-v4.6:latest` | `e95583acac77` | 1.525 | 752.16M | Q4_K_M | 262144 | local | completion, thinking, tools, vision | vision | TESTABLE_EXPECTED |
| `minimax-m3:cloud` | `d03a959f45c0` | 0.0 | 0 | - | 524288 | cloud | completion, thinking, tools, vision | vision | CLOUD_ONLY |
| `ministral-3:8b` | `1922accd5827` | 5.609 | 8.9B | Q4_K_M | 262144 | local | completion, tools, vision | vision | TESTABLE_WITH_CPU_OFFLOAD |
| `mistral:7b` | `6577803aa9a0` | 4.073 | 7.2B | Q4_K_M | 32768 | local | completion, tools | general_or_unknown | TESTABLE_EXPECTED |
| `nemotron-3-nano:4b` | `6cc467f05439` | 2.643 | 4.0B | Q4_K_M | 262144 | local | completion, thinking, tools | general_or_unknown | TESTABLE_EXPECTED |
| `olmo-3:7b-instruct` | `ea72df8c85d7` | 4.165 | 7.3B | Q4_K_M | 65536 | local | completion, tools | general_or_unknown | TESTABLE_EXPECTED |
| `olmo-3:7b-think` | `b8d4c92ac9c1` | 4.165 | 7.3B | Q4_K_M | 65536 | local | completion, thinking | reasoning_name_hint | TESTABLE_EXPECTED |
| `openbmb/minicpm5:Q4_K_M` | `08239e8f70e0` | 0.641 | 1.1B | Q4_K_M | 131072 | local | completion, thinking, tools | general_or_unknown | TESTABLE_EXPECTED |
| `ornith:9b` | `a75697c14589` | 5.243 | 9.0B | Q4_K_M | 262144 | local | completion, thinking, tools | general_or_unknown | TESTABLE_WITH_CPU_OFFLOAD |
| `phi4-mini-reasoning:latest` | `3ca8c2865ce9` | 2.936 | 3.8B | Q4_K_M | 131072 | local | completion, tools | reasoning_name_hint | TESTABLE_EXPECTED |
| `phi4-mini:latest` | `78fad5d182a7` | 2.321 | 3.8B | Q4_K_M | 131072 | local | completion, tools | general_or_unknown | TESTABLE_EXPECTED |
| `qwen3-coder-next:cloud` | `aa626c11ae8d` | 0.0 | 80B | FP8 | - | cloud | - | code_name_hint | CLOUD_ONLY |
| `qwen3-coder:480b-cloud` | `e30e45586389` | 0.0 | 480B | BF16 | - | cloud | - | code_name_hint | CLOUD_ONLY |
| `qwen3-embedding:latest` | `64b933495768` | 4.356 | 7.6B | Q4_K_M | 40960 | local | embedding, tools | embedding | TESTABLE_EXPECTED |
| `qwen3-vl:8b` | `901cae732162` | 5.719 | 8.8B | Q4_K_M | 262144 | local | completion, thinking, tools, vision | vision | TESTABLE_WITH_CPU_OFFLOAD |
| `qwen3.5:4b` | `2a654d98e6fb` | 3.157 | 4.7B | Q4_K_M | 262144 | local | completion, thinking, tools, vision | vision | TESTABLE_EXPECTED |
| `qwen3.5:9b` | `6488c96fa5fa` | 6.142 | 9.7B | Q4_K_M | 262144 | local | completion, thinking, tools, vision | vision | TESTABLE_WITH_CPU_OFFLOAD |
| `rnj-1:latest` | `d20e29ab8d0f` | 4.763 | 8.3B | Q4_K_M | 32768 | local | completion, tools | general_or_unknown | TESTABLE_EXPECTED |
| `shieldgemma:2b` | `5aad5044d142` | 1.591 | 2.6B | Q4_K_M | 8192 | local | completion | safety | TESTABLE_EXPECTED |
| `smollm2:1.7b` | `cef4a1e09247` | 1.695 | 1.7B | Q8_0 | 8192 | local | completion, tools | general_or_unknown | TESTABLE_EXPECTED |
| `starcoder2:7b` | `1550ab21b10d` | 3.765 | 7B | Q4_0 | 16384 | local | completion, insert | code_name_hint | TESTABLE_EXPECTED |
| `translategemma:latest` | `c49d986b0764` | 3.072 | 4.3B | Q4_K_M | 131072 | local | completion, vision | vision | TESTABLE_EXPECTED |

## Engineering Caveat

The code harness has AST restrictions, no imports, restricted builtins, isolated `python -I -S`, a temporary working directory and timeout, but it is not an OS-level container/firewall sandbox. A real Ollama execution adapter is intentionally not enabled until architect-owned manifests and policies are frozen.
