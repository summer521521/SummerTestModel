# SummerTestModel Benchmark 1.0-rc1 Final Phase Report

[中文](final_report.zh-CN.md) · [English]

## Technical summary: RC1 should be the sole baseline for future incremental evaluation

This phase completed all 39 selected local models across 1,938 applicable task records, plus a separate 142-record reference run for two cloud models. All 1,938 raw records were then regraded offline under the practical policy, and one relaxed recovery was limited to 50 timeout, truncation, or tool-anomaly items across eight models. Thirty-nine recovery results were selected into the practical snapshot; six items still lack a scoreable final. The strict baseline and raw evidence remain intact, with no missing raw, duplicate key, scoring error, or infrastructure gap.

The main value is not a universal leaderboard. It is a sustainable protocol: frozen tasks and scorers, track-specific comparison, recorded digests/quantization/runtime, infrastructure failures separated from capability failures, and offline regrading by default. The most useful conclusions are:

- **Default local general/agent references:** `Qwen3-8B Q4_K_M` and `qwen3-vl:8b`; both reach Core 0.879, Tools 0.909, and Long Context 1.000, while Qwen3-VL adds Code 0.890 and Vision 1.000.
- **General and long-context work:** `gemma4:e4b`, `qwen3.5:9b`, and the two Qwen references; their Long Context means are 1.000 under practical scoring, but each has only four fixtures.
- **Speed-first work:** `granite4:7b-a1b-h`, `lfm2.5:8b`, and `MiniCPM5-1B`; high throughput does not imply high general capability, so use them for specific tool/code/translation roles.
- **Code:** `olmo-3:7b-think` 0.900, `qwen3-vl:8b` 0.890, `ornith:9b` 0.810, and `deepseek-r1:8b` 0.775; each must be read beside its timeout, truncation, and provenance evidence.
- **Specialists:** use `qwen3-embedding` for embeddings and `Granite Guardian` for safety. `GLM-OCR` reaches semantic 0.810 but 0% completion, while `DeepSeek-OCR` reaches 0.792 with 100% completion; score alone is insufficient.
- **Medical:** `nemotron-3-nano:4b`, `qwen3.5:4b`, and `qwen3.5:9b` each reach 0.800 on the current fixtures, which is not evidence of clinical validity or safety.

![Top ten local RC1 core scores](assets/rc1_core_top10.png)

Figure 1. Models with Core records; each has 24 RC1 Core records and the bar is the 0–1 within-track mean.

## Why the benchmark is designed this way

1. **Local scope is explicit.** The formal baseline contains installed local models around or below 10B total parameters. Cloud models are a separate reference so server-side capability is not mixed with local hardware constraints.
2. **Tracks stay independent.** Core, Reasoning, Code, Translation, Tools, Vision, OCR, Long Context, Embedding, Safety, Medical, and Performance are interpreted separately. There is no universal overall score that penalizes specialists for inapplicable work.
3. **Runtime evidence has two explicit layers.** The strict baseline preserves its original profile boundaries. A one-attempt relaxed budget applies only to the frozen 50-item recovery queue and never silently replaces original evidence.
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
| Strict score | Original RC1 scorer result under the frozen runtime boundary, preserved for audit |
| Practical score | Offline regrade of existing raw plus selected recovery evidence; tracks remain independent |
| Coverage | Scored records divided by records for that model/track, not global inventory coverage |
| Performance | Ollama token/duration fields and wall time; contributes no capability points |
| Runtime anomaly | Stream interruption, tool loop, timeout, or truncation; distinct from infrastructure failure |
| Publisher comparison | Context for expected role only unless dataset, precision, prompt, runtime, and scorer are reproduced |

The machine is Windows 11 with an Intel i5-13500HX, 31.8 GiB RAM, and an RTX 4060 Laptop GPU with 8 GiB VRAM. The strict baseline recorded Ollama 0.32.6 and targeted recovery recorded 0.32.9. Patch versions are environment metadata, not permanent gates.

## Quality, speed, and stability must be read together

### 1. Balance matters more than winning one track

Under practical scoring, `Qwen3-8B Q4_K_M` and `qwen3-vl:8b` both reach Core 0.879, Tools 0.909, and Long Context 1.000. Qwen3-8B is the stable text reference; Qwen3-VL adds Code 0.890 and Vision 1.000. `gemma4:e4b` also reaches Core 0.879 and Translation/Long Context 1.000, but Code is only 0.200. There is no workload-free winner.

### 2. Throughput and general quality show a real trade-off

![Local speed and Core trade-off](assets/rc1_speed_core_tradeoff.png)

Figure 2. Local generation models with both Core and performance records; bubble size approximates model-file size. Performance is descriptive and contributes no capability score.

`MiniCPM5-1B`, `LFM2.5`, and `Granite 4 7B-A1B` remain high-throughput choices. Practical regrading changes semantic/protocol attribution, but speed still contributes no capability points. Select candidates by workload first, then compare throughput within that workload.

### 3. Reasoning models often think without producing a timely final answer

`DeepSeek-R1-0528-Qwen3-8B`, `DeepSeek-R1 8B`, `OLMo Think`, and `Phi-4-mini-reasoning` accumulate truncation or before-final failures. Under the practical-local boundary, that is usability evidence: lengthy thinking does not count as a correct answer if no scoreable final arrives.

![Models with the most runtime issues](assets/rc1_runtime_issues.png)

Figure 3. Recorded issue events for the most affected models. These events are not equivalent to infrastructure outages and do not automatically enter capability denominators.

### 4. Specialists must be interpreted in their native role

`qwen3-embedding` scored 1.000 on 12 small retrieval queries, but this does not reproduce MTEB. `Granite Guardian` scored 1.000 on 20 safety samples and should be used as a judge, not a chat model. `GLM-OCR` simultaneously has semantic mean 0.810 and 0% completion, proving why semantic correctness, degeneration, and completion must remain separate. StarCoder2's base completion role also differs from instruction-style pure functions.

## Recommendations by use case

| Use case | First choice | Alternatives | Rationale |
| --- | --- | --- | --- |
| Default local assistant | Qwen3-8B Q4 | Qwen3-VL 8B, Gemma4 E4B, Nemotron 4B | Balanced Core, tools, translation, and context |
| Code | OLMo Think / Qwen3-VL 8B | Ornith 9B, DeepSeek-R1 8B, MiniCPM5 | Practical Code 0.900 / 0.890; choose by stability and provenance |
| Tool use | Qwen3-8B / Qwen3-VL / LFM2.5 | Falcon H1R, Gemma4, Qwen3.5 | Leaders are near 0.90; also inspect loop and unknown-tool events |
| Translation | Gemma4 / Qwen3-8B | Granite4.1, Ministral3, TranslateGemma | Current translation means 0.967–1.000 |
| Long context | Qwen3-8B / Qwen3-VL / Gemma4 / Qwen3.5 | Several 1.000 candidates | Only four fixtures; not a 128K/1M limit test |
| Low-resource throughput | MiniCPM5 1B | Granite4 A1B, LFM2.5, SmolLM2 | Fast, but not equivalent in general quality |
| Safety classification | Granite Guardian 8B | ShieldGemma 2B | 1.000 vs 0.708; Shield uses fewer resources |
| Embedding retrieval | Qwen3 Embedding | No peer in current baseline | Passed all 12 small retrieval fixtures |
| OCR | DeepSeek OCR (experimental) | GLM-OCR (semantic only), Qwen3.5 / Qwen3-VL | Read semantic score and completion together |
| Medical text | Nemotron 4B / Qwen3.5 (research) | Falcon H1R / MedGemma | Fixture result only, not medical validation |

## Every model: expectation, observed behavior, and recommendation

Expected role comes from installed metadata and mapped publisher model cards. Observed behavior is RC1-only. Recommendations and cautions are project guidance, not a new scorer or retention decision.

| Model | Size / quant | Expected role | Observed locally | Recommended use | Caution | Source |
| --- | --- | --- | --- | --- | --- | --- |
| `deepscaler:1.5b` | 1.8B / F16 | reasoning candidate | Long context 1.000; Core 0.802; Reasoning 0.800; Translation 0.717 | Low-cost candidate for fast reasoning or code drafts. | Tools remain weak and three truncations remain; validate complex agent work. | [Official source](https://huggingface.co/agentica-org/DeepScaleR-1.5B-Preview) |
| `deepseek-ocr:latest` | 3.3B / F16 | OCR specialist | OCR 0.792 | The most promising local OCR specialist in the current track. | Practical semantic score is 0.792, but the small fixture set is not production evidence. | [Official source](https://huggingface.co/deepseek-ai/DeepSeek-OCR) |
| `deepseek-r1:8b` | 8.2B / Q4_K_M | reasoning candidate | Long context 1.000; Translation 0.950; Reasoning 0.778 (completion 90%); Code 0.775 | Useful for code and translation when latency is acceptable. | After recovery it still has one timeout, one truncation, and seven interrupted streams, so it is not a stable interactive default. | [Official source](https://huggingface.co/deepseek-ai/DeepSeek-R1) |
| `functiongemma:270m` | 268.10M / Q8_0 | tool-calling specialist | Tools 0.575 | Keep as a tiny tool-router research target. | Practical Tools is 0.575; treat it as a tiny routing experiment, not a complex multi-turn agent. | [Official source](https://ai.google.dev/gemma/docs/functiongemma/model_card) |
| `gemma3n:e4b` | 6.9B / Q4_K_M | multimodal/general candidate | Translation 0.833; Core 0.827; Code 0.200 | Lightweight translation, summarization, and ordinary text work. | Code is only 0.200, and multimodal execution was not confirmed by the current manifest. | [Official source](https://huggingface.co/google/gemma-3n-E4B-it) |
| `gemma4:e4b` | 8.0B / Q4_K_M | vision or multimodal candidate | Translation 1.000; Long context 1.000; Tools 0.905; Core 0.879 | One of the best local choices for general, translation, and long-context work. | Code remains only 0.200 after practical regrading; use it for its text and long-context strengths. | [Official source](https://ai.google.dev/gemma/docs/core/model_card_4) |
| `glm-ocr:latest` | 1.1B / F16 | OCR specialist | OCR 0.810 (completion 0%) | Useful for OCR semantic-recognition research with explicit deduplication and termination control. | Semantic score is 0.810, but all 10 outputs truncated and completion is 0%; this is not deliverable OCR. | [Official source](https://huggingface.co/zai-org/GLM-OCR) |
| `granite4.1-guardian:8b` | 8.4B / Q6_K | safety specialist | Safety 1.000 | Current first choice for dedicated input/output safety classification. | Use only as a safety judge, not as a chat model. | [Official source](https://huggingface.co/ibm-granite/granite-guardian-4.1-8b) |
| `granite4.1:8b` | 8.8B / Q4_K_M | general candidate | Long context 1.000; Translation 0.967; Tools 0.884; Core 0.844 | Stable multilingual general assistant and enterprise-text candidate. | Code and tools are mid-tier rather than best-in-class locally. | [Official source](https://huggingface.co/ibm-granite/granite-4.1-8b) |
| `granite4:7b-a1b-h` | 6.9B / Q4_K_M | general candidate | Long context 1.000; Translation 0.917; Tools 0.889; Core 0.702 | Speed-oriented candidate for code, translation, and tool use. | Practical Core is 0.702, but the exact upstream artifact mapping remains uncertain. | [Official source](https://huggingface.co/ibm-granite) |
| `hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M` | 3.4B / Q4_K_M | vision or multimodal candidate | Long context 1.000; Translation 0.883; Vision 0.875; Core 0.702 | Lightweight document-vision integration experiments and translation. | Vision is 0.875 and OCR 0.370; visual fixtures improved, but OCR remains unreliable. | [Official source](https://huggingface.co/ibm-granite/granite-vision-4.1-4b) |
| `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | 8.19B / Q4_K_M | general candidate | Translation 1.000; Long context 1.000; Tools 0.909; Core 0.879 | The strongest current default for the local general/agent baseline. | Long-context practical score is 1.000 on only four fixtures, with two truncations still recorded. | [Official source](https://huggingface.co/Qwen/Qwen3-8B) |
| `hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M` | 7.59B / Q4_K_M | general candidate | Long context 1.000; Translation 0.950; Tools 0.907; Core 0.879 | A solid comparison model for reasoning, general, and medical text tasks. | Code is 0.500 and it is slower than several 4B or hybrid alternatives. | [Official source](https://huggingface.co/tiiuae/Falcon-H1R-7B) |
| `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | 3.08B / Q4_K_M | general candidate | Long context 1.000; Translation 0.850; Reasoning 0.800; Core 0.756 | Small, fast model for translation and lightweight text processing. | Weak core, code, and tools performance; avoid complex agent work. | [Official source](https://huggingface.co/HuggingFaceTB/SmolLM3-3B) |
| `huggingface.co/llmware/phi-4-mini-gguf:latest` | 3.84B / Q4_K_M | general candidate | Long context 1.000; Translation 0.800; Core 0.723; Tools 0.477 | Low-footprint fallback for ordinary Q&A and translation. | Code 0.315 and Tools 0.477 still require strong validation on complex work. | [Official source](https://huggingface.co/microsoft/Phi-4-mini-instruct) |
| `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest` | 8.19B / Q4_K_M | reasoning candidate | Translation 0.917; Reasoning 0.800; Long context 0.750; Code 0.665 | Offline reasoning or code drafts where research workflows tolerate failures. | Practical Core is only 0.429, with substantial timeout, anomaly, and truncation evidence retained. | [Official source](https://huggingface.co/deepseek-ai/DeepSeek-R1-0528-Qwen3-8B) |
| `kaelri/hy-mt2:7b-q4_K_M` | 7.5B / Q4_K_M | translation specialist | Translation 0.800 | Dedicated translation comparison model. | Translation 0.800 trails several general models here; do not extrapolate to other capabilities. | [Official source](https://huggingface.co/tencent/Hy-MT2-7B) |
| `lfm2.5:8b` | 8.5B / Q4_K_M | general candidate | Long context 1.000; Tools 0.909; Translation 0.883; Core 0.838 | Speed-first candidate for tool use and reasoning. | Practical Core 0.838 and Tools 0.909 are promising, but broader fixtures are needed for generalization. | [Official source](https://huggingface.co/LiquidAI/LFM2.5-8B-A1B) |
| `llama3.2:3b` | 3.2B / Q4_K_M | general candidate | Long context 1.000; Translation 0.867; Tools 0.820; Core 0.748 | Lightweight code, tool use, and multilingual text work. | Practical Core is 0.748; complex instructions still need validation against tool and code behavior. | [Official source](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct) |
| `medgemma1.5:4b` | 4.3B / Q4_K_M | medical/multimodal specialist | Medical 0.717; OCR 0.488 (completion 90%) | Use only for medical-model integration diagnosis and future targeted retesting. | Medical is 0.717 and OCR 0.488 on small fixtures; never use this for real clinical decisions. | [Official source](https://developers.google.com/health-ai-developer-foundations/medgemma/model-card) |
| `minicpm-v4.6:latest` | 752.16M / Q4_K_M | vision or multimodal candidate | Long context 1.000; Translation 0.933; Tools 0.909; Core 0.863 | Extremely fast candidate for translation and lightweight text. | Vision is 0.750 and OCR 0.463, but local parameter metadata still has identity anomalies. | [Official source](https://huggingface.co/openbmb/MiniCPM-V-4_6) |
| `ministral-3:8b` | 8.9B / Q4_K_M | vision or multimodal candidate | Long context 1.000; Translation 0.967; Core 0.879; Tools 0.876 | Balanced multilingual, code, tool, and multimodal candidate. | Vision is 0.750 on only eight fixtures, and speed is not a strength. | [Official source](https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512) |
| `mistral:7b` | 7.2B / Q4_K_M | general candidate | Translation 0.900; Tools 0.767; Long context 0.750; Core 0.748 | Stable traditional 7B multilingual baseline. | Tools 0.767 and Long Context 0.750 are useful but not current track leaders. | [Official source](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3) |
| `nemotron-3-nano:4b` | 4.0B / Q4_K_M | general candidate | Long context 1.000; Tools 0.826 (completion 88%); Core 0.808; Reasoning 0.800 | Priority 4B candidate for general, medical-text, and medium-speed agent tasks. | Translation is weaker and one unknown tool call occurred; medical results do not imply clinical safety. | [Official source](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8) |
| `olmo-3:7b-instruct` | 7.3B / Q4_K_M | general candidate | Long context 1.000; Translation 0.933; Core 0.832; Tools 0.822 | Transparent comparison model for open research, general text, and translation. | Code 0.400 and the overall profile still trail the strongest group. | [Official source](https://huggingface.co/allenai/Olmo-3-7B-Instruct) |
| `olmo-3:7b-think` | 7.3B / Q4_K_M | reasoning candidate | Long context 1.000 (completion 75%); Code 0.900; Translation 0.850; Core 0.837 (completion 96%) | Code and reasoning research when longer waits are acceptable. | After recovery it still has two before-final truncations and one timeout, so it is unsuitable for latency-sensitive interaction. | [Official source](https://huggingface.co/allenai/Olmo-3-7B-Think) |
| `openbmb/minicpm5:Q4_K_M` | 1.1B / Q4_K_M | general candidate | Long context 1.000; Tools 0.891; Translation 0.850; Core 0.802 | Ultra-light, very high-throughput candidate for code and translation. | Practical regrading improves its profile, but two truncations remain; tiny size does not imply complex-task reliability. | [Official source](https://huggingface.co/openbmb/MiniCPM5-1B) |
| `ornith:9b` | 9.0B / Q4_K_M | general candidate | Translation 0.933; Tools 0.884; Code 0.810; Core 0.808 | Strong local candidate for code, general, and translation tasks. | Practical Reasoning is 0.800, but no authoritative exact model card was matched. | Unverified |
| `phi4-mini-reasoning:latest` | 3.8B / Q4_K_M | reasoning candidate | Long context 1.000; Core 0.827; Reasoning 0.800; Translation 0.700 | Mathematical reasoning experiments and lightweight offline analysis. | Multiple truncations remain; improved practical scores do not imply latency-sensitive stability. | [Official source](https://huggingface.co/microsoft/Phi-4-mini-reasoning) |
| `phi4-mini:latest` | 3.8B / Q4_K_M | general candidate | Long context 1.000; Translation 0.833; Medical 0.664; Core 0.611 | Fast fallback for ordinary text and translation. | Core 0.611, Code 0.240, and Tools 0.477 limit complex agent use. | [Official source](https://huggingface.co/microsoft/Phi-4-mini-instruct) |
| `qwen3-embedding:latest` | 7.6B / Q4_K_M | embedding specialist | Embedding 1.000 | Clear current choice for local semantic retrieval and embeddings. | A perfect small-fixture score does not reproduce MTEB and the model is not for text generation. | [Official source](https://huggingface.co/Qwen/Qwen3-Embedding-8B) |
| `qwen3-vl:8b` | 8.8B / Q4_K_M | vision or multimodal candidate | Translation 1.000; Vision 1.000; Long context 1.000; Tools 0.909 | The strongest current balance across code, tools, and vision. | One timeout and one truncation remain; Vision 1.000 covers only eight small fixtures. | [Official source](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct) |
| `qwen3.5:4b` | 4.7B / Q4_K_M | vision or multimodal candidate | Long context 1.000; Translation 0.967; Tools 0.886; Vision 0.875 | 4B-class candidate for general, tools, and lightweight multimodal work. | Targeted recovery selected 14 improved results, but two before-final truncations remain; long outputs still need control. | [Official source](https://huggingface.co/Qwen/Qwen3.5-4B) |
| `qwen3.5:9b` | 9.7B / Q4_K_M | vision or multimodal candidate | Long context 1.000; Translation 0.967; Tools 0.904; Core 0.879 | High-quality candidate for general and long-context tasks. | All nine recovery items became scoreable, but Code 0.410 still trails peer code candidates. | [Official source](https://huggingface.co/Qwen/Qwen3.5-9B) |
| `rnj-1:latest` | 8.3B / Q4_K_M | general candidate | Long context 1.000; Translation 0.933; Tools 0.889; Core 0.829 | Responsive practical model for code, STEM, and translation. | Practical Core is 0.829, but strong prompting and validation remain necessary. | [Official source](https://huggingface.co/EssentialAI/rnj-1) |
| `shieldgemma:2b` | 2.6B / Q4_K_M | safety specialist | Safety 0.708 | Low-resource first-pass safety screening. | Safety composite is 0.708, below Granite Guardian; review high-impact decisions. | [Official source](https://huggingface.co/google/shieldgemma-2b) |
| `smollm2:1.7b` | 1.7B / Q8_0 | general candidate | Translation 0.783; Tools 0.732 (completion 75%); Core 0.581; Code 0.560 | Low-resource text generation, translation, and simple code drafts. | Tool recovery improved substantially, but two loop-limit events remain; cap rounds for complex agent work. | [Official source](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct) |
| `starcoder2:7b` | 7B / Q4_0 | code-completion specialist | Code 0.000 | Continue only in a dedicated code-completion or FIM workflow. | It is a base completion model; RC1 instruction-style pure-function code scored 0 and does not match its native use. | [Official source](https://huggingface.co/bigcode/starcoder2-7b) |
| `translategemma:latest` | 4.3B / Q4_K_M | translation specialist | Translation 0.900; OCR 0.603 | Stable dedicated translation model and translation-quality comparator. | OCR 0.603 is outside its native role; do not extrapolate to general chat or document understanding. | [Official source](https://huggingface.co/google/translategemma-4b-it) |

## How to compare publisher data with local results

Publisher benchmarks describe potential under specific datasets, precision, templates, runtimes, and hardware. RC1 describes usability for the installed quantized artifact through Ollama on this machine. Use publisher evidence to establish expected role, inspect whether the local direction is consistent, and only then decide whether reproducing the exact official benchmark is worthwhile. Never subtract an RC1 mean such as 0.879 from MMLU, HumanEval, MTEB, or OmniDocBench percentages.

Key verified positioning includes Qwen3 thinking/non-thinking operation, Gemma4 multimodal and long-context positioning, Granite 4.1 instruction/tool use, and Granite Guardian safety judging. Each model row links its mapped official source. `ornith:9b` still lacks a trustworthy exact model-card match, so provenance should be resolved before strong conclusions.

## Operational cautions

- Vision/OCR fixtures are small. Practical semantic scores are more permissive, but completion and repetition remain separate evidence.
- Thinking tokens do not enter ordinary answer scoring; long reasoning without a final answer is not scored as correct.
- Code covers restricted pure functions behind an AST gate and isolated child process, not full repository engineering.
- Safety and Medical are small targeted fixtures; a perfect safety score or medical leader is not domain validation.
- Performance is comparable only on this machine under the recorded quantization and background conditions. Cloud wall time and local tokens/s remain separate.
- Digest, quantization, template, and Ollama version are recorded. Version change alone does not block incremental testing; a changed digest is a new model revision.
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
- [Practical model-by-track rows](../public_results/rc1_practical_track_scores.csv)
- [Fifty-item targeted recovery comparison](../public_results/rc1_practical_recovery_20260813.csv)
- [Strict baseline model-by-track rows](../public_results/rc1_track_scores.csv)
- [Performance data](../public_results/rc1_performance.csv)
- [Failure analysis](rc1_failure_analysis.md)
- [Official source mapping](../inventory/official_model_references.csv)
- [Machine profile](machine_profile.md)
- [Historical reference](legacy_history.md)

Updated on 2026-08-14: the strict RC1 baseline remains unchanged, while the default presentation uses the practical offline regrade plus selected targeted recovery evidence. The website and future reports are generated from the same sanitized structured data.
