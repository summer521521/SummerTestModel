# Official Claims Comparison

## Interpretation rule

Publisher numbers and RC1 results answer different questions. Official cards generally use upstream weights, a stated precision/runtime, public benchmark datasets, and publisher prompts. RC1 uses the installed Ollama digest and quantization on this machine with frozen local tasks. The table therefore records whether the local artifact can be mapped to an official source, but does not subtract or equate percentages across the two systems.

Examples of useful context:

- [Gemma 4 E4B](https://ai.google.dev/gemma/docs/core/model_card_4) is officially 4.5B effective / 8B total with 128K context, while this project classifies resource size by total parameters and local disk footprint.
- [GLM-OCR](https://huggingface.co/zai-org/GLM-OCR)'s publisher OmniDocBench claim describes the official evaluation stack; RC1's small OCR fixtures expose local truncation and repetition behavior and are not a reproduction of OmniDocBench.
- [StarCoder2](https://huggingface.co/bigcode/starcoder2-7b) is officially a code-completion base model rather than a chat instruction model, which is important context for strict instruction-following failures.
- [ShieldGemma](https://huggingface.co/google/shieldgemma-2b) and [Granite Guardian](https://huggingface.co/ibm-granite/granite-guardian-4.1-8b) are safety specialists and appear only in their applicable track, not a general leaderboard.

## Source coverage

Authoritative or family-level sources were matched for 38/39 local entries. Unverified mappings remain explicit rather than inferred from model self-description.

The complete machine-readable mapping, claims summary, digest, and confidence label is in `inventory/official_model_references.csv`.

## Representative claim-to-observation analysis

| Installed artifact | Publisher context | RC1 observation on this machine | Interpretation |
| --- | --- | --- | --- |
| `gemma4:e4b` | Official E4B card: MMLU-Pro 69.4%, AIME 2026 42.5%, LiveCodeBench v6 52.0%, MMMU-Pro 52.6%; 4.5B effective / 8B total | Core 0.736, reasoning 0.400, code 0.000, translation 1.000, vision 0.125 | Strong local core/translation but the strict RC1 code and vision fixtures do not reproduce the publisher stack; quantization, prompting, safe harness, and task scale differ. |
| `hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M` | Official card: AIME24 88.1%, LiveCodeBench v6 68.6%, GPQA-D 61.3%, MMLU-Pro 72.1% | Core 0.653, reasoning 0.500, code 0.375 | Useful local reasoning signal, but much lower RC1 code/reasoning means cannot be read as a failed reproduction of those unrelated datasets. |
| `granite4.1:8b` | Official card: MMLU 73.84%, MMLU-Pro 55.99%, HumanEval 85.37%, BFCL 68.27% | Core 0.569, code 0.375, tools 0.500, translation 0.967 | Translation was robust locally; code/tool gaps are specific to RC1 protocol, hidden tests, and Ollama Q4 artifact. |
| `glm-ocr:latest` | Official card reports OmniDocBench 94.62 and an SDK throughput figure | OCR semantic 0.000; all 10 RC1 outputs were truncated/repetition-degenerated | The installed model-only Ollama path did not reproduce the official OCR pipeline. This is an integration/usability finding, not evidence that the publisher OmniDocBench number is false. |
| `qwen3-embedding:latest` | Official card reports multilingual MTEB score 70.58 | RC1 embedding NDCG@5 1.000 on 12 queries | Perfect small-fixture retrieval is encouraging but far too narrow to imply an MTEB-equivalent result. |
| `phi4-mini:latest` | Official card: 3.8B/128K, MMLU 67.3%, BBH 70.4% | Core 0.278, code 0.113, translation 0.833 | Translation transferred better than strict core/code protocol behavior in this quantized local runtime. |
| `starcoder2:7b` | Official card identifies a code-completion base model and self-reports HumanEval 35.4 / HumanEval+ 29.9 | RC1 code 0.000 | The mismatch is expected: RC1 asks for instruction-following pure functions, while the upstream artifact is not a chat instruction model. |

These rows are interpretive comparisons, not a shared leaderboard. Exact official links and match-confidence labels are retained in the source matrix.
