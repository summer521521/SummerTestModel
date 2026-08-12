#!/usr/bin/env python3
"""Build public RC1 summaries from sanitized, derived result JSONL files.

This module never reads or writes private raw responses. It intentionally keeps
the local baseline and cloud reference comparison in separate scopes and does
not calculate an overall universal score.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
LOCAL_RESULTS = ROOT / "public_results" / "rc1_baseline_20260809.scorer-1.0-rc1.1.jsonl"
CLOUD_RESULTS = ROOT / "public_results" / "rc1_cloud_comparison_20260812.jsonl"
INVENTORY = ROOT / "inventory" / "model_inventory.csv"


TRACK_PREFIXES = (
    ("CORE_", "core"),
    ("RSN_", "reasoning"),
    ("CODE_", "code"),
    ("TRANS_", "translation"),
    ("TOOL_", "tools"),
    ("VIS_", "vision"),
    ("OCR_", "ocr"),
    ("CTX", "long_context"),
    ("EMB_", "embedding"),
    ("SAFE", "safety"),
    ("UNSAFE", "safety"),
    ("MED_", "medical"),
    ("PERF_", "performance"),
)


SCORE_FIELDS = {
    "core": "task_score",
    "reasoning": "task_score",
    "code": "score",
    "translation": "normalized_score_0_to_1",
    "tools": "score",
    "vision": "score",
    "ocr": "semantic_score",
    "long_context": "score",
    "embedding": "ndcg_at_5",
    "safety": "accuracy",
    "medical": "score",
}


OFFICIAL_REFERENCES: dict[str, dict[str, str]] = {
    "deepscaler:1.5b": {
        "official_model": "agentica-org/DeepScaleR-1.5B-Preview",
        "source_url": "https://huggingface.co/agentica-org/DeepScaleR-1.5B-Preview",
        "match_confidence": "FAMILY_MATCH",
        "publisher_claim": "1.5B reasoning model; publisher reports math/reasoning benchmark results.",
    },
    "deepseek-ocr:latest": {
        "official_model": "deepseek-ai/DeepSeek-OCR",
        "source_url": "https://huggingface.co/deepseek-ai/DeepSeek-OCR",
        "match_confidence": "EXACT_FAMILY_QUANTIZED_RUNTIME",
        "publisher_claim": "Document OCR model with publisher-reported OmniDocBench results.",
    },
    "deepseek-r1:8b": {
        "official_model": "DeepSeek-R1 family",
        "source_url": "https://huggingface.co/deepseek-ai/DeepSeek-R1",
        "match_confidence": "FAMILY_ONLY_LOCAL_TAG_AMBIGUOUS",
        "publisher_claim": "Reasoning family with published math, coding, and knowledge evaluations.",
    },
    "functiongemma:270m": {
        "official_model": "google/functiongemma-270m-it",
        "source_url": "https://ai.google.dev/gemma/docs/functiongemma/model_card",
        "match_confidence": "EXACT_FAMILY_QUANTIZED_RUNTIME",
        "publisher_claim": "270M specialist intended for function calling, not general conversation.",
    },
    "gemma3n:e4b": {
        "official_model": "google/gemma-3n-E4B-it",
        "source_url": "https://huggingface.co/google/gemma-3n-E4B-it",
        "match_confidence": "EXACT_FAMILY_QUANTIZED_RUNTIME",
        "publisher_claim": "Mobile-oriented multimodal E4B model; official card distinguishes effective and total parameters.",
    },
    "gemma4:e4b": {
        "official_model": "Gemma 4 E4B",
        "source_url": "https://ai.google.dev/gemma/docs/core/model_card_4",
        "match_confidence": "EXACT_FAMILY_QUANTIZED_RUNTIME",
        "publisher_claim": "4.5B effective / 8B total, 128K, multimodal; official card publishes MMLU-Pro, AIME, code and vision results.",
    },
    "glm-ocr:latest": {
        "official_model": "zai-org/GLM-OCR",
        "source_url": "https://huggingface.co/zai-org/GLM-OCR",
        "match_confidence": "EXACT_FAMILY_RUNTIME_VARIANT",
        "publisher_claim": "1B OCR model; publisher reports OmniDocBench 94.62 and SDK throughput.",
    },
    "granite4.1-guardian:8b": {
        "official_model": "ibm-granite/granite-guardian-4.1-8b",
        "source_url": "https://huggingface.co/ibm-granite/granite-guardian-4.1-8b",
        "match_confidence": "EXACT_FAMILY_QUANTIZED_RUNTIME",
        "publisher_claim": "8B safety/risk-detection specialist with official risk taxonomy and evaluation guidance.",
    },
    "granite4.1:8b": {
        "official_model": "ibm-granite/granite-4.1-8b",
        "source_url": "https://huggingface.co/ibm-granite/granite-4.1-8b",
        "match_confidence": "EXACT_FAMILY_QUANTIZED_RUNTIME",
        "publisher_claim": "Official card publishes MMLU, MMLU-Pro, HumanEval and BFCL results.",
    },
    "granite4:7b-a1b-h": {
        "official_model": "IBM Granite 4 7B-A1B family",
        "source_url": "https://huggingface.co/ibm-granite",
        "match_confidence": "FAMILY_MATCH",
        "publisher_claim": "Hybrid/MoE Granite family; exact Ollama artifact mapping requires release metadata.",
    },
    "hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M": {
        "official_model": "ibm-granite/granite-vision-4.1-4b",
        "source_url": "https://huggingface.co/ibm-granite/granite-vision-4.1-4b",
        "match_confidence": "EXACT_QUANTIZED_DERIVATIVE",
        "publisher_claim": "4B document/vision specialist; official card provides document-understanding evaluations.",
    },
    "hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M": {
        "official_model": "Qwen/Qwen3-8B",
        "source_url": "https://huggingface.co/Qwen/Qwen3-8B",
        "match_confidence": "EXACT_QUANTIZED_DERIVATIVE",
        "publisher_claim": "8.2B total, 32K native context; official card describes thinking/non-thinking modes.",
    },
    "hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M": {
        "official_model": "tiiuae/Falcon-H1R-7B",
        "source_url": "https://huggingface.co/tiiuae/Falcon-H1R-7B",
        "match_confidence": "EXACT_QUANTIZED_DERIVATIVE",
        "publisher_claim": "7B reasoning model; publisher reports AIME, LiveCodeBench, GPQA-D and MMLU-Pro.",
    },
    "hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL": {
        "official_model": "HuggingFaceTB/SmolLM3-3B",
        "source_url": "https://huggingface.co/HuggingFaceTB/SmolLM3-3B",
        "match_confidence": "EXACT_QUANTIZED_DERIVATIVE",
        "publisher_claim": "3B dual-mode reasoning model; official card publishes separate thinking and non-thinking results.",
    },
    "huggingface.co/llmware/phi-4-mini-gguf:latest": {
        "official_model": "microsoft/Phi-4-mini-instruct",
        "source_url": "https://huggingface.co/microsoft/Phi-4-mini-instruct",
        "match_confidence": "QUANTIZED_DERIVATIVE_REPACKAGER",
        "publisher_claim": "3.8B, 128K; official card publishes MMLU and BBH results.",
    },
    "huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest": {
        "official_model": "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B",
        "source_url": "https://huggingface.co/deepseek-ai/DeepSeek-R1-0528-Qwen3-8B",
        "match_confidence": "EXACT_QUANTIZED_DERIVATIVE",
        "publisher_claim": "8B distilled reasoning model with official math and reasoning evaluations.",
    },
    "kaelri/hy-mt2:7b-q4_K_M": {
        "official_model": "tencent/Hy-MT2-7B",
        "source_url": "https://huggingface.co/tencent/Hy-MT2-7B",
        "match_confidence": "QUANTIZED_DERIVATIVE_REPACKAGER",
        "publisher_claim": "7B translation specialist with publisher-reported multilingual translation evaluations.",
    },
    "lfm2.5:8b": {
        "official_model": "LiquidAI/LFM2.5-8B-A1B",
        "source_url": "https://huggingface.co/LiquidAI/LFM2.5-8B-A1B",
        "match_confidence": "EXACT_FAMILY_QUANTIZED_RUNTIME",
        "publisher_claim": "8B-A1B efficient hybrid model; official card reports instruction, code and tool-use evaluations.",
    },
    "llama3.2:3b": {
        "official_model": "meta-llama/Llama-3.2-3B-Instruct",
        "source_url": "https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct",
        "match_confidence": "EXACT_FAMILY_QUANTIZED_RUNTIME",
        "publisher_claim": "3B instruction model with official multilingual text evaluations.",
    },
    "medgemma1.5:4b": {
        "official_model": "Google MedGemma 1.5 4B",
        "source_url": "https://developers.google.com/health-ai-developer-foundations/medgemma/model-card",
        "match_confidence": "EXACT_FAMILY_QUANTIZED_RUNTIME",
        "publisher_claim": "4B medical multimodal specialist; official guidance requires task-specific validation.",
    },
    "minicpm-v4.6:latest": {
        "official_model": "openbmb/MiniCPM-V-4_6",
        "source_url": "https://huggingface.co/openbmb/MiniCPM-V-4_6",
        "match_confidence": "FAMILY_MATCH_RUNTIME_METADATA_ODD",
        "publisher_claim": "Multimodal MiniCPM-V 4.6 family; local parameter metadata should not be treated as authoritative provenance.",
    },
    "ministral-3:8b": {
        "official_model": "mistralai/Ministral-3-8B-Instruct-2512",
        "source_url": "https://huggingface.co/mistralai/Ministral-3-8B-Instruct-2512",
        "match_confidence": "EXACT_FAMILY_QUANTIZED_RUNTIME",
        "publisher_claim": "8B instruction model; official card describes long-context and multimodal capabilities.",
    },
    "mistral:7b": {
        "official_model": "mistralai/Mistral-7B-Instruct-v0.3",
        "source_url": "https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3",
        "match_confidence": "FAMILY_ONLY_LOCAL_REVISION_UNVERIFIED",
        "publisher_claim": "7B instruction family with function-calling support; local tag revision is not explicit.",
    },
    "nemotron-3-nano:4b": {
        "official_model": "nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8",
        "source_url": "https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-FP8",
        "match_confidence": "FAMILY_MATCH_DIFFERENT_QUANTIZATION",
        "publisher_claim": "4B efficient model; official card provides reasoning, coding and agentic evaluations.",
    },
    "olmo-3:7b-instruct": {
        "official_model": "allenai/Olmo-3-7B-Instruct",
        "source_url": "https://huggingface.co/allenai/Olmo-3-7B-Instruct",
        "match_confidence": "EXACT_FAMILY_QUANTIZED_RUNTIME",
        "publisher_claim": "7B instruction variant with official evaluation tables and open training documentation.",
    },
    "olmo-3:7b-think": {
        "official_model": "allenai/Olmo-3-7B-Think",
        "source_url": "https://huggingface.co/allenai/Olmo-3-7B-Think",
        "match_confidence": "EXACT_FAMILY_QUANTIZED_RUNTIME",
        "publisher_claim": "7B thinking variant with official reasoning evaluations.",
    },
    "openbmb/minicpm5:Q4_K_M": {
        "official_model": "openbmb/MiniCPM5-1B",
        "source_url": "https://huggingface.co/openbmb/MiniCPM5-1B",
        "match_confidence": "EXACT_QUANTIZED_DERIVATIVE",
        "publisher_claim": "1.08B total hybrid reasoning/tool model with 131K context claim.",
    },
    "ornith:9b": {
        "official_model": "UNVERIFIED",
        "source_url": "",
        "match_confidence": "UNVERIFIED_LOCAL_TAG",
        "publisher_claim": "No authoritative exact model card was matched during this audit.",
    },
    "phi4-mini-reasoning:latest": {
        "official_model": "microsoft/Phi-4-mini-reasoning",
        "source_url": "https://huggingface.co/microsoft/Phi-4-mini-reasoning",
        "match_confidence": "EXACT_FAMILY_QUANTIZED_RUNTIME",
        "publisher_claim": "3.8B, 128K reasoning specialist trained for mathematical reasoning.",
    },
    "phi4-mini:latest": {
        "official_model": "microsoft/Phi-4-mini-instruct",
        "source_url": "https://huggingface.co/microsoft/Phi-4-mini-instruct",
        "match_confidence": "EXACT_FAMILY_QUANTIZED_RUNTIME",
        "publisher_claim": "3.8B, 128K instruction model; official card publishes MMLU and BBH results.",
    },
    "qwen3-embedding:latest": {
        "official_model": "Qwen/Qwen3-Embedding-8B",
        "source_url": "https://huggingface.co/Qwen/Qwen3-Embedding-8B",
        "match_confidence": "EXACT_FAMILY_QUANTIZED_RUNTIME",
        "publisher_claim": "8B embedding specialist; official card reports multilingual MTEB results.",
    },
    "qwen3-vl:8b": {
        "official_model": "Qwen/Qwen3-VL-8B-Instruct",
        "source_url": "https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct",
        "match_confidence": "EXACT_FAMILY_QUANTIZED_RUNTIME",
        "publisher_claim": "8B vision-language instruction model with official multimodal evaluations.",
    },
    "qwen3.5:4b": {
        "official_model": "Qwen/Qwen3.5-4B",
        "source_url": "https://huggingface.co/Qwen/Qwen3.5-4B",
        "match_confidence": "EXACT_FAMILY_QUANTIZED_RUNTIME",
        "publisher_claim": "4B current Qwen family model; official card publishes capability and benchmark tables.",
    },
    "qwen3.5:9b": {
        "official_model": "Qwen/Qwen3.5-9B",
        "source_url": "https://huggingface.co/Qwen/Qwen3.5-9B",
        "match_confidence": "EXACT_FAMILY_QUANTIZED_RUNTIME",
        "publisher_claim": "9B current Qwen family model; official card publishes capability and benchmark tables.",
    },
    "rnj-1:latest": {
        "official_model": "EssentialAI/rnj-1",
        "source_url": "https://huggingface.co/EssentialAI/rnj-1",
        "match_confidence": "FAMILY_ONLY_BASE_VS_INSTRUCT_UNVERIFIED",
        "publisher_claim": "8B code/STEM family; official card distinguishes base and instruction variants.",
    },
    "shieldgemma:2b": {
        "official_model": "google/shieldgemma-2b",
        "source_url": "https://huggingface.co/google/shieldgemma-2b",
        "match_confidence": "EXACT_FAMILY_QUANTIZED_RUNTIME",
        "publisher_claim": "2B safety content-moderation specialist targeting four harm categories.",
    },
    "smollm2:1.7b": {
        "official_model": "HuggingFaceTB/SmolLM2-1.7B-Instruct",
        "source_url": "https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct",
        "match_confidence": "EXACT_FAMILY_RUNTIME_REVISION_UNVERIFIED",
        "publisher_claim": "1.7B compact instruction model with official small-model evaluations.",
    },
    "starcoder2:7b": {
        "official_model": "bigcode/starcoder2-7b",
        "source_url": "https://huggingface.co/bigcode/starcoder2-7b",
        "match_confidence": "EXACT_FAMILY_QUANTIZED_RUNTIME",
        "publisher_claim": "7B code-completion base model, not an instruction-tuned chat model; official card reports HumanEval.",
    },
    "translategemma:latest": {
        "official_model": "google/translategemma-4b-it",
        "source_url": "https://huggingface.co/google/translategemma-4b-it",
        "match_confidence": "FAMILY_MATCH_LOCAL_TAG_SIZE_4B",
        "publisher_claim": "4B translation specialist; official model card defines multimodal translation usage.",
    },
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not an object")
            records.append(value)
    return records


def task_track(task_id: str) -> str:
    for prefix, track in TRACK_PREFIXES:
        if task_id.startswith(prefix):
            return track
    raise ValueError(f"unknown task prefix: {task_id}")


def capability_score(record: dict[str, Any], track: str) -> float | None:
    field = SCORE_FIELDS.get(track)
    if field is None:
        return None
    value = (record.get("score") or {}).get(field)
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * q
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def summarize_scope(records: list[dict[str, Any]], scope: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    task_records = [r for r in records if r.get("record_type", "task_result") == "task_result"]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in task_records:
        grouped[(task_track(record["task_id"]), record["model"])].append(record)

    scores: list[dict[str, Any]] = []
    performance: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for (track, model), group in sorted(grouped.items()):
        statuses = Counter(str(r.get("inference_status") or "unknown") for r in group)
        runtime_anomalies = sum(bool(r.get("runtime_anomaly")) for r in group)
        truncations = sum("truncated" in str(r.get("inference_status") or "") for r in group)
        numerical = [s for r in group if (s := capability_score(r, track)) is not None]
        if track != "performance":
            scores.append(
                {
                    "scope": scope,
                    "track": track,
                    "model": model,
                    "records": len(group),
                    "scored_records": len(numerical),
                    "coverage": round(len(numerical) / len(group), 6) if group else 0.0,
                    "mean_score_0_to_1": round(statistics.fmean(numerical), 6) if numerical else "",
                    "runtime_anomalies": runtime_anomalies,
                    "truncation_related": truncations,
                }
            )
        else:
            wall = [float(t["client_wall_seconds"]) for r in group if isinstance((t := r.get("timing") or {}).get("client_wall_seconds"), (int, float))]
            ttft = [float(t["time_to_first_token"]) for r in group if isinstance((t := r.get("timing") or {}).get("time_to_first_token"), (int, float))]
            output_tps = [float(t["output_tokens_per_second"]) for r in group if isinstance((t := r.get("timing") or {}).get("output_tokens_per_second"), (int, float))]
            performance.append(
                {
                    "scope": scope,
                    "model": model,
                    "records": len(group),
                    "wall_seconds_mean": round(statistics.fmean(wall), 6) if wall else "",
                    "wall_seconds_p50": round(percentile(wall, 0.5) or 0.0, 6) if wall else "",
                    "wall_seconds_p95": round(percentile(wall, 0.95) or 0.0, 6) if wall else "",
                    "ttft_seconds_mean": round(statistics.fmean(ttft), 6) if ttft else "",
                    "output_tokens_per_second_mean": round(statistics.fmean(output_tps), 6) if output_tps else "",
                    "runtime_anomalies": runtime_anomalies,
                }
            )

        for status, count in sorted(statuses.items()):
            if status != "completed":
                failures.append(
                    {
                        "scope": scope,
                        "model": model,
                        "track": track,
                        "category": status,
                        "count": count,
                        "layer": "model_or_runtime" if status not in {"network_error", "server_error", "unavailable"} else "infrastructure",
                    }
                )
        if runtime_anomalies:
            failures.append(
                {
                    "scope": scope,
                    "model": model,
                    "track": track,
                    "category": "runtime_anomaly",
                    "count": runtime_anomalies,
                    "layer": "runtime",
                }
            )

    for record in records:
        if record.get("record_type") == "model_availability":
            failures.append(
                {
                    "scope": scope,
                    "model": record.get("model"),
                    "track": "availability",
                    "category": record.get("status", "unavailable"),
                    "count": 1,
                    "layer": "provider_availability",
                }
            )
    return scores, performance, failures


def official_reference_rows() -> list[dict[str, Any]]:
    with INVENTORY.open("r", encoding="utf-8-sig", newline="") as handle:
        inventory = list(csv.DictReader(handle))
    rows: list[dict[str, Any]] = []
    for model in inventory:
        if model["local_or_cloud"] != "local":
            continue
        ref = OFFICIAL_REFERENCES.get(model["exact_name"], {})
        rows.append(
            {
                "model": model["exact_name"],
                "digest": model["digest"],
                "parameter_size": model["parameter_size"],
                "quantization": model["quantization"],
                "official_model": ref.get("official_model", "UNVERIFIED"),
                "official_source_url": ref.get("source_url", ""),
                "match_confidence": ref.get("match_confidence", "UNVERIFIED"),
                "publisher_claim_summary": ref.get("publisher_claim", "No authoritative exact model card was matched during this audit."),
                "comparison_rule": "CONTEXT_ONLY_NOT_NUMERICALLY_COMPARABLE_TO_RC1",
            }
        )
    if len(rows) != 39:
        raise ValueError(f"expected 39 local inventory rows, got {len(rows)}")
    return rows


def markdown_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> list[str]:
    output = ["| " + " | ".join(label for _, label in columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        output.append("| " + " | ".join(str(row.get(key, "")).replace("|", "\\|") for key, _ in columns) + " |")
    return output


def build_docs(scores: list[dict[str, Any]], performance: list[dict[str, Any]], failures: list[dict[str, Any]]) -> None:
    ranked: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in scores:
        if row["mean_score_0_to_1"] != "":
            ranked[(row["scope"], row["track"])].append(row)
    for group in ranked.values():
        group.sort(key=lambda x: (-float(x["mean_score_0_to_1"]), x["model"]))

    lines = [
        "# SummerTestModel Benchmark 1.0-rc1 Results",
        "",
        "## Publication boundary",
        "",
        "This snapshot evaluates practical usability on one Windows/Ollama machine. It is not a controlled laboratory comparison. Ollama version, machine profile, quantization, runtime defaults, and run date are recorded as environment metadata rather than fixed cross-era gates.",
        "",
        "The 39-model local baseline and the cloud comparison are separate scopes. There is no universal overall score, and specialist tracks are not penalized for inapplicable tasks. Publisher benchmark claims use different prompts, runtimes, precision, datasets, and scoring rules; they are context, not directly comparable RC1 scores.",
        "",
        "## Data integrity",
        "",
        "- Local baseline: 39/39 models, 1,938 derived records, 1,938 immutable raw files, no missing raw, no duplicate inference key.",
        "- Offline scorer release: `1.0-rc1.1`; repaired three scorer crashes without changing model output.",
        "- Cloud reference: 2 models tested for 142 tasks; 3 provider-retired entries retained as HTTP 410 availability evidence.",
        "- Infrastructure failures are excluded from capability denominators; none occurred in the completed local or cloud task records.",
        "",
        "## Local track leaders",
        "",
        "Scores below are within-track means only. Vision and OCR are experimental because the small fixture set and strict scoring produce low absolute values.",
        "",
    ]
    local_leaders: list[dict[str, Any]] = []
    for (scope, track), group in sorted(ranked.items()):
        if scope != "local" or track == "performance":
            continue
        for rank, row in enumerate(group[:3], 1):
            local_leaders.append({"track": track, "rank": rank, **row})
    lines.extend(markdown_table(local_leaders, [("track", "Track"), ("rank", "Rank"), ("model", "Model"), ("mean_score_0_to_1", "Mean"), ("scored_records", "Scored"), ("records", "Records")]))
    lines.extend(["", "## Cloud reference", "", "Cloud results do not enter the local baseline or retention decisions.", ""])
    cloud_rows: list[dict[str, Any]] = []
    for (scope, track), group in sorted(ranked.items()):
        if scope == "cloud":
            for rank, row in enumerate(group, 1):
                cloud_rows.append({"track": track, "rank": rank, **row})
    lines.extend(markdown_table(cloud_rows, [("track", "Track"), ("rank", "Rank"), ("model", "Model"), ("mean_score_0_to_1", "Mean"), ("records", "Records")]))
    lines.extend(
        [
            "",
            "## Performance telemetry",
            "",
            "Performance telemetry is descriptive and adds no capability points. Cloud endpoints do not expose comparable server-side eval duration, so local output tokens/s and cloud wall time must not be mixed into one speed leaderboard.",
            "",
            "See `public_results/rc1_performance.csv` for per-model fields.",
            "",
            "## Known limitations",
            "",
            "- The RC1 task set is compact and some tracks are experimental.",
            "- Model quantization, chat template, thinking defaults, and Ollama/runtime behavior materially affect observed results.",
            "- `truncated_before_final` means the budget ended before a distinct final answer; it is not an infrastructure outage.",
            "- Publisher claims are not reproduced unless the exact official benchmark, precision, prompt, and runtime are separately implemented.",
            "- Retention remains `UNASSESSED`; this report does not declare models dominated or delete them.",
        ]
    )
    (ROOT / "docs" / "rc1_results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    failure_lines = [
        "# RC1 Failure Analysis",
        "",
        "## Executive finding",
        "",
        "The completed baseline has no missing raw evidence, duplicate inference, runner exception, or unresolved infrastructure failure. The visible error population is dominated by bounded generation/truncation, non-terminal streams after meaningful output, tool-loop behavior, and one corrected scorer implementation defect.",
        "",
        "## Scorer defect corrected offline",
        "",
        "`CORE_PRACT_04` previously raised `TypeError: unhashable type: 'dict'` for three models because the scorer converted an object-containing array to a set. The scorer now validates every list element is a string before set comparison. Raw responses were not changed; all 1,938 records were regraded with scorer `1.0-rc1.1`, repairing all three scorer errors.",
        "",
        "Affected models: `granite4:7b-a1b-h`, `olmo-3:7b-instruct`, and `hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M`.",
        "",
        "## Runtime and model-output findings",
        "",
        "- 7 absolute timeouts occurred in reasoning tasks. They are practical-local boundary results, not network failures.",
        "- 12 streams ended after meaningful output but before a terminal Ollama record. Their raw output remains scoreable and is tagged `stream_interrupted_after_output`.",
        "- 104 records are truncation-related: 66 `truncated` plus 38 `truncated_before_final`.",
        "- Tool-loop failures are bounded at three rounds. `nemotron-3-nano:4b` emitted a nonexistent tool name on `TOOL_07`; MiniCPM5 and SmolLM2 repeated or malformed calls on several tool tasks.",
        "- Cloud comparison had five `truncated_before_final` records and no infrastructure failure. Three other cloud catalog entries returned provider HTTP 410 and were recorded as unavailable, never capability score zero.",
        "",
        "## Resolution policy",
        "",
        "- Scorer defect: fix and offline regrade existing immutable raw (completed).",
        "- Wrong answer, malformed output, repetition, tool-name/argument error, timeout after generation, and truncation: preserve as model/runtime result; do not retry automatically.",
        "- Transport failure before meaningful output: use the frozen bounded retry/circuit-breaker policy.",
        "- Stream interruption after meaningful output: preserve and score available evidence, tag incomplete terminal metadata, and only targeted-rerun if a future explicitly approved study requires it.",
        "- Ollama patch-version drift: record as environment metadata. It is only blocking when the API is unavailable, a required capability is broken, or evidence integrity cannot be guaranteed.",
        "",
        "## Machine-readable counts",
        "",
        "See `public_results/rc1_failure_counts.csv`.",
    ]
    (ROOT / "docs" / "rc1_failure_analysis.md").write_text("\n".join(failure_lines) + "\n", encoding="utf-8")

    refs = official_reference_rows()
    official_lines = [
        "# Official Claims Comparison",
        "",
        "## Interpretation rule",
        "",
        "Publisher numbers and RC1 results answer different questions. Official cards generally use upstream weights, a stated precision/runtime, public benchmark datasets, and publisher prompts. RC1 uses the installed Ollama digest and quantization on this machine with frozen local tasks. The table therefore records whether the local artifact can be mapped to an official source, but does not subtract or equate percentages across the two systems.",
        "",
        "Examples of useful context:",
        "",
        "- [Gemma 4 E4B](https://ai.google.dev/gemma/docs/core/model_card_4) is officially 4.5B effective / 8B total with 128K context, while this project classifies resource size by total parameters and local disk footprint.",
        "- [GLM-OCR](https://huggingface.co/zai-org/GLM-OCR)'s publisher OmniDocBench claim describes the official evaluation stack; RC1's small OCR fixtures expose local truncation and repetition behavior and are not a reproduction of OmniDocBench.",
        "- [StarCoder2](https://huggingface.co/bigcode/starcoder2-7b) is officially a code-completion base model rather than a chat instruction model, which is important context for strict instruction-following failures.",
        "- [ShieldGemma](https://huggingface.co/google/shieldgemma-2b) and [Granite Guardian](https://huggingface.co/ibm-granite/granite-guardian-4.1-8b) are safety specialists and appear only in their applicable track, not a general leaderboard.",
        "",
        "## Source coverage",
        "",
        f"Authoritative or family-level sources were matched for {sum(r['official_source_url'] != '' for r in refs)}/39 local entries. Unverified mappings remain explicit rather than inferred from model self-description.",
        "",
        "The complete machine-readable mapping, claims summary, digest, and confidence label is in `inventory/official_model_references.csv`.",
        "",
        "## Representative claim-to-observation analysis",
        "",
        "| Installed artifact | Publisher context | RC1 observation on this machine | Interpretation |",
        "| --- | --- | --- | --- |",
        "| `gemma4:e4b` | [Official E4B card](https://ai.google.dev/gemma/docs/core/model_card_4): MMLU-Pro 69.4%, AIME 2026 42.5%, LiveCodeBench v6 52.0%, MMMU-Pro 52.6%; 4.5B effective / 8B total | Core 0.736, reasoning 0.400, code 0.000, translation 1.000, vision 0.125 | Strong local core/translation but the strict RC1 code and vision fixtures do not reproduce the publisher stack; quantization, prompting, safe harness, and task scale differ. |",
        "| `hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M` | [Official card](https://huggingface.co/tiiuae/Falcon-H1R-7B): AIME24 88.1%, LiveCodeBench v6 68.6%, GPQA-D 61.3%, MMLU-Pro 72.1% | Core 0.653, reasoning 0.500, code 0.375 | Useful local reasoning signal, but much lower RC1 code/reasoning means cannot be read as a failed reproduction of those unrelated datasets. |",
        "| `granite4.1:8b` | [Official card](https://huggingface.co/ibm-granite/granite-4.1-8b): MMLU 73.84%, MMLU-Pro 55.99%, HumanEval 85.37%, BFCL 68.27% | Core 0.569, code 0.375, tools 0.500, translation 0.967 | Translation was robust locally; code/tool gaps are specific to RC1 protocol, hidden tests, and Ollama Q4 artifact. |",
        "| `glm-ocr:latest` | [Official card](https://huggingface.co/zai-org/GLM-OCR) reports OmniDocBench 94.62 and an SDK throughput figure | OCR semantic 0.000; all 10 RC1 outputs were truncated/repetition-degenerated | The installed model-only Ollama path did not reproduce the official OCR pipeline. This is an integration/usability finding, not evidence that the publisher OmniDocBench number is false. |",
        "| `qwen3-embedding:latest` | [Official card](https://huggingface.co/Qwen/Qwen3-Embedding-8B) reports multilingual MTEB score 70.58 | RC1 embedding NDCG@5 1.000 on 12 queries | Perfect small-fixture retrieval is encouraging but far too narrow to imply an MTEB-equivalent result. |",
        "| `phi4-mini:latest` | [Official card](https://huggingface.co/microsoft/Phi-4-mini-instruct): 3.8B/128K, MMLU 67.3%, BBH 70.4% | Core 0.278, code 0.113, translation 0.833 | Translation transferred better than strict core/code protocol behavior in this quantized local runtime. |",
        "| `starcoder2:7b` | [Official card](https://huggingface.co/bigcode/starcoder2-7b) identifies a code-completion base model and self-reports HumanEval 35.4 / HumanEval+ 29.9 | RC1 code 0.000 | The mismatch is expected: RC1 asks for instruction-following pure functions, while the upstream artifact is not a chat instruction model. |",
        "",
        "These rows are interpretive comparisons, not a shared leaderboard. Exact official links and match-confidence labels are retained in the source matrix.",
    ]
    (ROOT / "docs" / "official_claims_comparison.md").write_text("\n".join(official_lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    if args.root.resolve() != ROOT.resolve():
        raise SystemExit("custom roots are not supported; run from this repository")

    local = read_jsonl(LOCAL_RESULTS)
    cloud = read_jsonl(CLOUD_RESULTS)
    local_scores, local_perf, local_failures = summarize_scope(local, "local")
    cloud_scores, cloud_perf, cloud_failures = summarize_scope(cloud, "cloud")
    scores = sorted(local_scores + cloud_scores, key=lambda r: (r["scope"], r["track"], -float(r["mean_score_0_to_1"] or -1), r["model"]))
    performance = sorted(local_perf + cloud_perf, key=lambda r: (r["scope"], r["model"]))
    failures = sorted(local_failures + cloud_failures, key=lambda r: (r["scope"], r["model"], r["track"], r["category"]))

    write_csv(ROOT / "public_results" / "rc1_track_scores.csv", ["scope", "track", "model", "records", "scored_records", "coverage", "mean_score_0_to_1", "runtime_anomalies", "truncation_related"], scores)
    write_csv(ROOT / "public_results" / "rc1_performance.csv", ["scope", "model", "records", "wall_seconds_mean", "wall_seconds_p50", "wall_seconds_p95", "ttft_seconds_mean", "output_tokens_per_second_mean", "runtime_anomalies"], performance)
    write_csv(ROOT / "public_results" / "rc1_failure_counts.csv", ["scope", "model", "track", "category", "count", "layer"], failures)
    refs = official_reference_rows()
    write_csv(ROOT / "inventory" / "official_model_references.csv", list(refs[0]), refs)
    build_docs(scores, performance, failures)

    local_task_records = [r for r in local if r.get("record_type", "task_result") == "task_result"]
    cloud_task_records = [r for r in cloud if r.get("record_type") == "task_result"]
    summary = {
        "benchmark_version": "1.0-rc1",
        "scorer_version": "1.0-rc1.1",
        "universal_overall_score": None,
        "local": {
            "models": len({r["model"] for r in local_task_records}),
            "task_records": len(local_task_records),
            "runtime_anomalies": sum(bool(r.get("runtime_anomaly")) for r in local_task_records),
            "truncation_related": sum("truncated" in str(r.get("inference_status") or "") for r in local_task_records),
            "scoring_errors": sum(r.get("scoring_status") == "scoring_error" for r in local_task_records),
            "infrastructure_failures": sum(r.get("inference_status") in {"network_error", "server_error", "unavailable"} for r in local_task_records),
        },
        "cloud_reference": {
            "models_tested": len({r["model"] for r in cloud_task_records}),
            "task_records": len(cloud_task_records),
            "unavailable_catalog_entries": sum(r.get("record_type") == "model_availability" for r in cloud),
            "scoring_errors": sum(r.get("scoring_status") == "scoring_error" for r in cloud_task_records),
            "infrastructure_failures_in_task_records": sum(r.get("inference_status") in {"network_error", "server_error", "unavailable"} for r in cloud_task_records),
        },
        "official_reference_rows": len(refs),
        "official_reference_urls": sum(bool(r["official_source_url"]) for r in refs),
        "artifacts": {
            "track_scores": "public_results/rc1_track_scores.csv",
            "performance": "public_results/rc1_performance.csv",
            "failure_counts": "public_results/rc1_failure_counts.csv",
            "official_references": "inventory/official_model_references.csv",
        },
    }
    encoded = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    (ROOT / "public_results" / "rc1_summary.json").write_text(encoded, encoding="utf-8")
    print(json.dumps({"status": "PASS", "local_records": len(local_task_records), "cloud_records": len(cloud_task_records), "summary_sha256": hashlib.sha256(encoded.encode()).hexdigest()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
