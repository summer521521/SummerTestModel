# SummerTestModel Benchmark 1.0-rc1 Final Phase Report

[中文](final_report.zh-CN.md) · [English]

## Technical summary: RC1 should be the sole baseline for future incremental evaluation

This phase completed all 39 selected local models across 1,938 applicable task records, plus a separate 142-record reference run for two cloud models. Every inference persists immutable raw evidence before normalization and scoring. There is no missing raw evidence, duplicate inference key, unresolved scoring error, or infrastructure-incomplete task record. Three scorer crashes were repaired through offline regrading without calling the models again.

The main value is not a universal leaderboard. It is a sustainable protocol: frozen tasks and scorers, track-specific comparison, recorded digests/quantization/runtime, infrastructure failures separated from capability failures, and offline regrading by default. The most useful conclusions are:

- **Default local general/agent baseline:** `Qwen3-8B Q4_K_M`; Core 0.778, Reasoning 0.500, Code 0.625, Translation 1.000, and Tools 0.750 make it the most balanced option.
- **General and long-context work:** `gemma4:e4b` and `qwen3.5:9b`; Gemma is stronger in translation, while Qwen3.5 9B is weak in code/translation and truncates before final more often.
- **Speed-first work:** `granite4:7b-a1b-h`, `lfm2.5:8b`, and `MiniCPM5-1B`; high throughput does not imply high general capability, so use them for specific tool/code/translation roles.
- **Code:** `qwen3-vl:8b`, `ornith:9b`, `deepseek-r1:8b`, and `olmo-3:7b-think`; each carries a different provenance, timeout, or truncation risk.
- **Specialists:** use `qwen3-embedding` for embeddings, `Granite Guardian` for safety classification, and `TranslateGemma` as a translation specialist; OCR and vision are not production-ready conclusions.
- **Medical:** `nemotron-3-nano:4b` led the current medical-text fixtures, which is not evidence of clinical validity or safety.

![Top ten local RC1 core scores](assets/rc1_core_top10.png)

Figure 1. Models with Core records; each has 24 RC1 Core records and the bar is the 0–1 within-track mean.

## Why the benchmark is designed this way

1. **Local scope is explicit.** The formal baseline contains installed local models around or below 10B total parameters. Cloud models are a separate reference so server-side capability is not mixed with local hardware constraints.
2. **Tracks stay independent.** Core, Reasoning, Code, Translation, Tools, Vision, OCR, Long Context, Embedding, Safety, Medical, and Performance are interpreted separately. There is no universal overall score that penalizes specialists for inapplicable work.
3. **Runtime boundaries are part of usability.** The 240-second Reasoning boundary and profile-specific context/output budgets answer whether a model is practical on this machine. A timeout or missing final remains evidence rather than triggering an unlimited extension.
4. **No constrained decoding assistance.** Tasks that request JSON still do not use `format=json`; protocol adherence is part of the tested capability.
5. **Thinking and final answers are separated.** Thinking is not concatenated into ordinary answers, and Reasoning only enables it for models whose metadata declares support.
6. **Evidence is layered.** Immutable inference, normalized interpretation, scorer output, and reports are separate, so scorer improvements do not require new inference.
7. **Failures are layered.** Network or service unavailability is distinct from a wrong answer. Transport errors receive at most one retry; semantic errors, timeout, truncation, and scorer failure do not trigger re-inference.
8. **Identity is revision-safe.** Keys include benchmark version, task-manifest hash, model digest, profile, and task ID. A changed digest is a new model revision.

## Data, metrics, and comparison boundaries

| Item | Definition |
| --- | --- |
| Local cohort | 39 installed local models; each model runs only applicable tracks |
| Task records | 1,938 local derived records mapped to 1,938 immutable local raw files |
| Score | Scorer output normalized to 0–1 and averaged within a track; tracks are never summed |
| Coverage | Scored records divided by records for that model/track, not global inventory coverage |
| Performance | Ollama token/duration fields and wall time; contributes no capability points |
| Runtime anomaly | Stream interruption, tool loop, timeout, or truncation; distinct from infrastructure failure |
| Publisher comparison | Context for expected role only unless dataset, precision, prompt, runtime, and scorer are reproduced |

The recorded machine is Windows 11 with an Intel i5-13500HX, 31.8 GiB RAM, and an RTX 4060 Laptop GPU with 8 GiB VRAM. The published snapshot used Ollama 0.32.6. Future runs record the current version rather than treating one patch version as a permanent gate.

## Quality, speed, and stability must be read together

### 1. Balance matters more than winning one track

`Qwen3-8B Q4_K_M` does not win every track, but it leads Core, ties the Reasoning/Translation/Tools leaders, and reaches 0.625 in Code. That makes it the strongest general reference for future additions. `gemma4:e4b` is also strong at Core 0.736, Translation 1.000, and Long Context 0.500, but its Code score is 0, so workload still determines the correct default.

### 2. Throughput and general quality show a real trade-off

![Local speed and Core trade-off](assets/rc1_speed_core_tradeoff.png)

Figure 2. Local generation models with both Core and performance records; bubble size approximates model-file size. Performance is descriptive and contributes no capability score.

`MiniCPM5-1B`, `LFM2.5`, and `Granite 4 7B-A1B` are very fast, but their Core means are 0.139, 0.072, and 0.361. Qwen3-8B, the Core leader, produces roughly 46.7 tokens/s. Select candidates by workload first, then compare speed within that workload.

### 3. Reasoning models often think without producing a timely final answer

`DeepSeek-R1-0528-Qwen3-8B`, `DeepSeek-R1 8B`, `OLMo Think`, and `Phi-4-mini-reasoning` accumulate truncation or before-final failures. Under the practical-local boundary, that is usability evidence: lengthy thinking does not count as a correct answer if no scoreable final arrives.

![Models with the most runtime issues](assets/rc1_runtime_issues.png)

Figure 3. Recorded issue events for the most affected models. These events are not equivalent to infrastructure outages and do not automatically enter capability denominators.

### 4. Specialists must be interpreted in their native role

`qwen3-embedding` scored 1.000 on 12 small retrieval queries, but this does not reproduce MTEB. `Granite Guardian` scored 1.000 on 20 safety samples and should be used as a judge, not a chat model. `StarCoder2` is a base code-completion model that scored 0 on instruction-style pure functions; that mainly exposes a task-shape mismatch. Low OCR/vision scores may also include prompting, preprocessing, template, or Ollama-integration effects.

## Recommendations by use case

| Use case | First choice | Alternatives | Rationale |
| --- | --- | --- | --- |
| Default local assistant | Qwen3-8B Q4 | Gemma4 E4B, Nemotron 4B | Balanced Core and agent tracks |
| Code | Qwen3-VL 8B | Ornith 9B, DeepSeek-R1 8B, OLMo Think, RNJ-1 | Strong current Code results; choose by stability and provenance |
| Tool use | Qwen3-8B / LFM2.5 / Qwen3-VL | Granite4 7B-A1B, Llama3.2 | Tools 0.750 or 0.625 |
| Translation | Gemma4 / Qwen3-8B | Granite4.1, Ministral3, TranslateGemma | Current translation means 0.967–1.000 |
| Long context | Gemma4 / Qwen3.5 9B | Several 0.250 alternatives | The current maximum is only 0.500 |
| Low-resource throughput | MiniCPM5 1B | Granite4 A1B, LFM2.5, SmolLM2 | Fast, but not equivalent in general quality |
| Safety classification | Granite Guardian 8B | ShieldGemma 2B | 1.000 vs 0.750; Shield uses fewer resources |
| Embedding retrieval | Qwen3 Embedding | No peer in current baseline | Passed all 12 small retrieval fixtures |
| OCR | DeepSeek OCR (experimental) | Granite Vision / Qwen3-VL (experimental) | Absolute scores remain too low for production |
| Medical text | Nemotron 4B (research) | Falcon H1R / Qwen3.5 9B | Fixture result only, not medical validation |

## Every model: expectation, observed behavior, and recommendation

Expected role comes from installed metadata and mapped publisher model cards. Observed behavior is RC1-only. Recommendations and cautions are project guidance, not a new scorer or retention decision.

| Model | Size / quant | Expected role | Observed locally | Recommended use | Caution | Source |
| --- | --- | --- | --- | --- | --- | --- |
| `deepscaler:1.5b` | 1.8B / F16 | reasoning candidate | Translation 0.717; Code 0.613; Reasoning 0.453; Core 0.139 | Low-cost candidate for fast reasoning or code drafts. | Weak core, tools, and long-context results; three truncations. | [Official source](https://huggingface.co/agentica-org/DeepScaleR-1.5B-Preview) |
| `deepseek-ocr:latest` | 3.3B / F16 | OCR specialist | OCR 0.384 | The most promising local OCR specialist in the current track. | Semantic score is only 0.384; not production-reliable OCR yet. | [Official source](https://huggingface.co/deepseek-ai/DeepSeek-OCR) |
| `deepseek-r1:8b` | 8.2B / Q4_K_M | reasoning candidate | Translation 0.950; Code 0.750; Reasoning 0.400; Long context 0.250 | Useful for code and translation when latency is acceptable. | Two absolute timeouts, nine runtime anomalies, and repeated truncation make it a poor default interactive model. | [Official source](https://huggingface.co/deepseek-ai/DeepSeek-R1) |
| `functiongemma:270m` | 268.10M / Q8_0 | tool-calling specialist | Tools 0.000 | Keep as a tiny tool-router research target. | RC1 tools score is 0; the current template and tool path are not yet proven usable. | [Official source](https://ai.google.dev/gemma/docs/functiongemma/model_card) |
| `gemma3n:e4b` | 6.9B / Q4_K_M | multimodal/general candidate | Translation 0.833; Core 0.361; Code 0.000 | Lightweight translation, summarization, and ordinary text work. | Code scored 0, and multimodal execution was not confirmed by the current manifest. | [Official source](https://huggingface.co/google/gemma-3n-E4B-it) |
| `gemma4:e4b` | 8.0B / Q4_K_M | vision or multimodal candidate | Translation 1.000; Core 0.736; Tools 0.625; Long context 0.500 | One of the best local choices for general, translation, and long-context work. | RC1 code score is 0 and absolute vision performance is low. | [Official source](https://ai.google.dev/gemma/docs/core/model_card_4) |
| `glm-ocr:latest` | 1.1B / F16 | OCR specialist | OCR 0.000 | Retain only to diagnose the gap between the official OCR pipeline and the Ollama integration. | All 10 outputs truncated and RC1 OCR score is 0. | [Official source](https://huggingface.co/zai-org/GLM-OCR) |
| `granite4.1-guardian:8b` | 8.4B / Q6_K | safety specialist | Safety 1.000 | Current first choice for dedicated input/output safety classification. | Use only as a safety judge, not as a chat model. | [Official source](https://huggingface.co/ibm-granite/granite-guardian-4.1-8b) |
| `granite4.1:8b` | 8.8B / Q4_K_M | general candidate | Translation 0.967; Core 0.569; Tools 0.500; Code 0.375 | Stable multilingual general assistant and enterprise-text candidate. | Code and tools are mid-tier rather than best-in-class locally. | [Official source](https://huggingface.co/ibm-granite/granite-4.1-8b) |
| `granite4:7b-a1b-h` | 6.9B / Q4_K_M | general candidate | Translation 0.917; Tools 0.625; Code 0.600; Core 0.361 | Speed-oriented candidate for code, translation, and tool use. | Core score is only 0.361 and the exact upstream artifact mapping remains uncertain. | [Official source](https://huggingface.co/ibm-granite) |
| `hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M` | 3.4B / Q4_K_M | vision or multimodal candidate | Translation 0.883; Code 0.250; Long context 0.250; Core 0.194 | Lightweight document-vision integration experiments and translation. | Vision 0.125 and OCR 0.100 did not reproduce strong document understanding on current fixtures. | [Official source](https://huggingface.co/ibm-granite/granite-vision-4.1-4b) |
| `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | 8.19B / Q4_K_M | general candidate | Translation 1.000; Core 0.778; Tools 0.750; Code 0.625 | The strongest current default for the local general/agent baseline. | Long-context scored 0.250 with two truncations; still choose by task. | [Official source](https://huggingface.co/Qwen/Qwen3-8B) |
| `hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M` | 7.59B / Q4_K_M | general candidate | Translation 0.950; Medical 0.667; Core 0.653; Tools 0.625 | A solid comparison model for reasoning, general, and medical text tasks. | Code scored 0.375 and it is slower than several 4B or hybrid alternatives. | [Official source](https://huggingface.co/tiiuae/Falcon-H1R-7B) |
| `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | 3.08B / Q4_K_M | general candidate | Translation 0.850; Reasoning 0.300; Code 0.125; Core 0.097 | Small, fast model for translation and lightweight text processing. | Weak core, code, and tools performance; avoid complex agent work. | [Official source](https://huggingface.co/HuggingFaceTB/SmolLM3-3B) |
| `huggingface.co/llmware/phi-4-mini-gguf:latest` | 3.84B / Q4_K_M | general candidate | Translation 0.800; Core 0.361; Long context 0.250; Code 0.237 | Low-footprint fallback for ordinary Q&A and translation. | Code 0.237 and tools 0 limit its value for complex work. | [Official source](https://huggingface.co/microsoft/Phi-4-mini-instruct) |
| `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | 8.19B / Q4_K_M | reasoning candidate | Translation 0.917; Code 0.613; Reasoning 0.430; Core 0.000 | Offline reasoning or code drafts where research workflows tolerate failures. | Core scored 0 with two absolute timeouts, seven anomalies, and 13 truncations. | [Official source](https://huggingface.co/deepseek-ai/DeepSeek-R1-0528-Qwen3-8B) |
| `kaelri/hy-mt2:7b-q4_K_M` | 7.5B / Q4_K_M | translation specialist | Translation 0.800 | Dedicated translation comparison model. | Translation 0.800 trails several general models here; do not extrapolate to other capabilities. | [Official source](https://huggingface.co/tencent/Hy-MT2-7B) |
| `lfm2.5:8b` | 8.5B / Q4_K_M | general candidate | Translation 0.883; Tools 0.750; Reasoning 0.500; Code 0.375 | Speed-first candidate for tool use and reasoning. | Core 0.072 and long-context 0 make it unsuitable as a general default. | [Official source](https://huggingface.co/LiquidAI/LFM2.5-8B-A1B) |
| `llama3.2:3b` | 3.2B / Q4_K_M | general candidate | Translation 0.867; Tools 0.625; Code 0.613; Core 0.278 | Lightweight code, tool use, and multilingual text work. | Core 0.278 indicates limited reliability on complex instructions. | [Official source](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct) |
| `medgemma1.5:4b` | 4.3B / Q4_K_M | medical/multimodal specialist | OCR 0.000; Medical 0.000 | Use only for medical-model integration diagnosis and future targeted retesting. | Medical and OCR both scored 0; never use this result for real clinical decisions. | [Official source](https://developers.google.com/health-ai-developer-foundations/medgemma/model-card) |
| `minicpm-v4.6:latest` | 752.16M / Q4_K_M | vision or multimodal candidate | Translation 0.933; Tools 0.500; Reasoning 0.400; Core 0.097 | Extremely fast candidate for translation and lightweight text. | Vision/OCR scored 0 and local parameter metadata has identity anomalies. | [Official source](https://huggingface.co/openbmb/MiniCPM-V-4_6) |
| `ministral-3:8b` | 8.9B / Q4_K_M | vision or multimodal candidate | Translation 0.967; Tools 0.625; Code 0.512; Core 0.486 | Balanced multilingual, code, tool, and multimodal candidate. | Absolute vision score is only 0.125 and speed is not a strength. | [Official source](https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512) |
| `mistral:7b` | 7.2B / Q4_K_M | general candidate | Translation 0.900; Core 0.361; Code 0.350; Tools 0.250 | Stable traditional 7B multilingual baseline. | Tools 0.250 and long-context 0 trail newer models on several tasks. | [Official source](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3) |
| `nemotron-3-nano:4b` | 4.0B / Q4_K_M | general candidate | Medical 0.833; Translation 0.733; Core 0.625; Code 0.500 | Priority 4B candidate for general, medical-text, and medium-speed agent tasks. | Translation is weaker and one unknown tool call occurred; medical results do not imply clinical safety. | [Official source](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8) |
| `olmo-3:7b-instruct` | 7.3B / Q4_K_M | general candidate | Translation 0.933; Core 0.528; Tools 0.500; Code 0.250 | Transparent comparison model for open research, general text, and translation. | Code 0.250 and overall track results do not reach the strongest group. | [Official source](https://huggingface.co/allenai/Olmo-3-7B-Instruct) |
| `olmo-3:7b-think` | 7.3B / Q4_K_M | reasoning candidate | Code 0.750; Translation 0.600; Core 0.569; Reasoning 0.430 | Code and reasoning research when longer waits are acceptable. | Seven before-final truncations and one timeout make it unsuitable for latency-sensitive interaction. | [Official source](https://huggingface.co/allenai/Olmo-3-7B-Think) |
| `openbmb/minicpm5:Q4_K_M` | 1.1B / Q4_K_M | general candidate | Translation 0.850; Code 0.688; Tools 0.500; Reasoning 0.230 | Ultra-light, very high-throughput candidate for code and translation. | Weak core/reasoning with nine truncations and two tool-loop limits. | [Official source](https://huggingface.co/openbmb/MiniCPM5-1B) |
| `ornith:9b` | 9.0B / Q4_K_M | general candidate | Translation 0.933; Code 0.762; Core 0.628; Tools 0.500 | Strong local candidate for code, general, and translation tasks. | Reasoning scored 0 and no authoritative exact model card was matched. | Unverified |
| `phi4-mini-reasoning:latest` | 3.8B / Q4_K_M | reasoning candidate | Translation 0.700; Reasoning 0.400; Code 0.362; Tools 0.125 | Mathematical reasoning experiments and lightweight offline analysis. | Nine truncations with limited core, code, and tools performance. | [Official source](https://huggingface.co/microsoft/Phi-4-mini-reasoning) |
| `phi4-mini:latest` | 3.8B / Q4_K_M | general candidate | Translation 0.833; Core 0.278; Long context 0.250; Medical 0.167 | Fast fallback for ordinary text and translation. | Core 0.278, code 0.113, and tools 0. | [Official source](https://huggingface.co/microsoft/Phi-4-mini-instruct) |
| `qwen3-embedding:latest` | 7.6B / Q4_K_M | embedding specialist | Embedding 1.000 | Clear current choice for local semantic retrieval and embeddings. | A perfect small-fixture score does not reproduce MTEB and the model is not for text generation. | [Official source](https://huggingface.co/Qwen/Qwen3-Embedding-8B) |
| `qwen3-vl:8b` | 8.8B / Q4_K_M | vision or multimodal candidate | Code 0.863; Tools 0.750; Translation 0.700; Core 0.569 | Strong current code and tools candidate with multimodal capability. | Vision is only 0.125 with timeouts and before-final truncation; do not infer visual reliability from the name. | [Official source](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct) |
| `qwen3.5:4b` | 4.7B / Q4_K_M | vision or multimodal candidate | Tools 0.625; Core 0.611; Translation 0.533; Medical 0.500 | 4B-class candidate for general, tools, and lightweight multimodal work. | Sixteen before-final truncations require strict control of long outputs. | [Official source](https://huggingface.co/Qwen/Qwen3.5-4B) |
| `qwen3.5:9b` | 9.7B / Q4_K_M | vision or multimodal candidate | Core 0.694; Medical 0.667; Tools 0.625; Translation 0.517 | High-quality candidate for general and long-context tasks. | Code and translation trail peers, with nine before-final truncations. | [Official source](https://huggingface.co/Qwen/Qwen3.5-9B) |
| `rnj-1:latest` | 8.3B / Q4_K_M | general candidate | Translation 0.933; Code 0.675; Tools 0.625; Core 0.403 | Responsive practical model for code, STEM, and translation. | Core is only 0.403, so strong prompting and validation remain necessary. | [Official source](https://huggingface.co/EssentialAI/rnj-1) |
| `shieldgemma:2b` | 2.6B / Q4_K_M | safety specialist | Safety 0.750 | Low-resource first-pass safety screening. | Safety accuracy 0.750 trails Granite Guardian; review high-impact decisions. | [Official source](https://huggingface.co/google/shieldgemma-2b) |
| `smollm2:1.7b` | 1.7B / Q8_0 | general candidate | Translation 0.783; Code 0.450; Core 0.236; Tools 0.125 | Low-resource text generation, translation, and simple code drafts. | Weak core/tools performance with five tool-loop limits. | [Official source](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct) |
| `starcoder2:7b` | 7B / Q4_0 | code-completion specialist | Code 0.000 | Continue only in a dedicated code-completion or FIM workflow. | It is a base completion model; RC1 instruction-style pure-function code scored 0 and does not match its native use. | [Official source](https://huggingface.co/bigcode/starcoder2-7b) |
| `translategemma:latest` | 4.3B / Q4_K_M | translation specialist | Translation 0.900; OCR 0.000 | Stable dedicated translation model and translation-quality comparator. | Do not treat OCR 0 as a translation failure or use it as a general chat model. | [Official source](https://huggingface.co/google/translategemma-4b-it) |

## How to compare publisher data with local results

Publisher benchmarks describe potential under specific datasets, precision, templates, runtimes, and hardware. RC1 describes usability for the installed quantized artifact through Ollama on this machine. Use publisher evidence to establish expected role, inspect whether the local direction is consistent, and only then decide whether reproducing the exact official benchmark is worthwhile. Never subtract an RC1 mean such as 0.778 from MMLU, HumanEval, MTEB, or OmniDocBench percentages.

Key verified positioning includes Qwen3 thinking/non-thinking operation, Gemma4 multimodal and long-context positioning, Granite 4.1 instruction/tool use, and Granite Guardian safety judging. Each model row links its mapped official source. `ornith:9b` still lacks a trustworthy exact model-card match, so provenance should be resolved before strong conclusions.

## Operational cautions

- Vision/OCR fixtures are small and strict; low scores may combine model, preprocessing, template, and runtime-integration effects.
- Thinking tokens do not enter ordinary answer scoring; long reasoning without a final answer is not scored as correct.
- Code covers restricted pure functions behind an AST gate and isolated child process, not full repository engineering.
- Safety and Medical are small targeted fixtures; a perfect safety score or medical leader is not domain validation.
- Performance is comparable only on this machine under the recorded quantization and background conditions. Cloud wall time and local tokens/s remain separate.
- A changed digest or quantization/runtime/template must be recorded. A changed digest becomes a new model revision.
- Retention remains `UNASSESSED`; use recommendations are not deletion decisions.

## The normalized workflow for adding future models

1. After `ollama pull`, inspect real metadata and digest instead of guessing from the name.
2. Select an explicit comparable reference assignment and run only applicable frozen tracks for the new model.
3. Persist task start, raw completion, and score completion separately; resume automatically skips valid terminal evidence.
4. Regrade existing raw evidence offline when scorers improve; do not regenerate model answers.
5. Export a new sanitized public result and append the new model to the same RC1 track tables without rerunning the original 39.
6. Consider a full rerun only for a major benchmark version, material inference-behavior change, or explicit annual/unified refresh.

See the [incremental model workflow](INCREMENTAL_MODELS.md) for commands and constraints.

## Limitations, further questions, and phase conclusion

The task set remains compact, with Vision/OCR/Medical especially experimental. Official benchmarks have not been reproduced with matching precision and runtime, and quantization, templates, and thinking implementations affect results. The next phase should not immediately rerun 39 models. It should add occasional new models and ask whether each one improves a defined niche at comparable resources, improves stability, or reproduces an official advantage through the Ollama path.

**The real phase output is a sustainable system, not merely a leaderboard:** RC1 is the normalized baseline, all 39 local models have complete evidence, scoring is decoupled from inference, failures are interpretable, and new models can be added without rerunning the baseline.

## Key artifacts

- [Interactive bilingual website](https://summertestmodel-benchmark.walker-ethan.chatgpt.site)
- [Full RC1 result report](rc1_results.md)
- [All model-by-track rows](../public_results/rc1_track_scores.csv)
- [Performance data](../public_results/rc1_performance.csv)
- [Failure analysis](rc1_failure_analysis.md)
- [Official source mapping](../inventory/official_model_references.csv)
- [Machine profile](machine_profile.md)
- [Historical reference](legacy_history.md)

This is a static RC1 snapshot published on 2026-08-12. The website and future incremental reports should be regenerated from the same structured data.
