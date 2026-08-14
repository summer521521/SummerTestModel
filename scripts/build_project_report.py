#!/usr/bin/env python3
"""Build the bilingual RC1 final report, model assessments, and report charts.

The builder reads only public inventory and derived result files. It does not
read private prompts, ground truth, hidden tests, or immutable raw responses.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
TRACKS = [
    "core", "reasoning", "code", "translation", "tools", "vision", "ocr",
    "long_context", "embedding", "safety", "medical",
]

TRACK_LABELS = {
    "core": ("通用能力", "Core"),
    "reasoning": ("推理", "Reasoning"),
    "code": ("代码", "Code"),
    "translation": ("翻译", "Translation"),
    "tools": ("工具调用", "Tools"),
    "vision": ("视觉", "Vision"),
    "ocr": ("OCR", "OCR"),
    "long_context": ("长上下文", "Long context"),
    "embedding": ("嵌入检索", "Embedding"),
    "safety": ("安全分类", "Safety"),
    "medical": ("医疗", "Medical"),
}

ROLE_LABELS = {
    "reasoning_name_hint": ("推理候选", "reasoning candidate"),
    "ocr": ("OCR 专用", "OCR specialist"),
    "tools": ("工具调用专用", "tool-calling specialist"),
    "safety": ("安全分类专用", "safety specialist"),
    "translation_name_hint": ("翻译专用", "translation specialist"),
    "code_name_hint": ("代码补全专用", "code-completion specialist"),
    "embedding": ("向量嵌入专用", "embedding specialist"),
    "vision": ("视觉/多模态候选", "vision or multimodal candidate"),
    "general_or_unknown": ("通用候选", "general candidate"),
    "": ("元数据角色未明确", "role not explicit in metadata"),
}

# A small number of installed artifacts expose a broad runtime capability (for
# example ``vision``) while the matched publisher card defines a narrower
# product role. These labels affect explanation only; they never affect task
# assignment, scoring, or retention.
ROLE_OVERRIDES = {
    "gemma3n:e4b": ("多模态/通用候选", "multimodal/general candidate"),
    "medgemma1.5:4b": ("医疗/多模态专用", "medical/multimodal specialist"),
    "translategemma:latest": ("翻译专用", "translation specialist"),
}

# Human interpretation is deliberately separate from the numeric scorer. These
# notes are project-owner guidance, not a new benchmark score or retention gate.
NOTES: dict[str, dict[str, str]] = {
    "deepscaler:1.5b": {
        "use_zh": "快速推理或代码草案的低成本候选。",
        "use_en": "Low-cost candidate for fast reasoning or code drafts.",
        "caution_zh": "工具表现偏弱，且仍有 3 次截断；复杂 Agent 任务需复核。",
        "caution_en": "Tools remain weak and three truncations remain; validate complex agent work.",
    },
    "deepseek-ocr:latest": {
        "use_zh": "当前 OCR 赛道中最值得继续研究的本地专用模型。",
        "use_en": "The most promising local OCR specialist in the current track.",
        "caution_zh": "实用语义分 0.792，但题量仍小，尚不足以视为可靠生产 OCR。",
        "caution_en": "Practical semantic score is 0.792, but the small fixture set is not production evidence.",
    },
    "deepseek-r1:8b": {
        "use_zh": "适合容忍等待时间的代码与翻译辅助。",
        "use_en": "Useful for code and translation when latency is acceptable.",
        "caution_zh": "宽松恢复后仍有 1 次超时、1 次截断和 7 次流中断，不适合稳定交互默认模型。",
        "caution_en": "After recovery it still has one timeout, one truncation, and seven interrupted streams, so it is not a stable interactive default.",
    },
    "functiongemma:270m": {
        "use_zh": "保留为极小工具路由器研究对象。",
        "use_en": "Keep as a tiny tool-router research target.",
        "caution_zh": "实用工具分 0.575，适合作为极小路由器实验而非复杂多轮 Agent。",
        "caution_en": "Practical Tools is 0.575; treat it as a tiny routing experiment, not a complex multi-turn agent.",
    },
    "gemma3n:e4b": {
        "use_zh": "轻量翻译、摘要和普通文本任务。",
        "use_en": "Lightweight translation, summarization, and ordinary text work.",
        "caution_zh": "代码仅 0.200，当前清单也未确认其多模态执行能力。",
        "caution_en": "Code is only 0.200, and multimodal execution was not confirmed by the current manifest.",
    },
    "gemma4:e4b": {
        "use_zh": "本机通用、翻译和长上下文任务的首选之一。",
        "use_en": "One of the best local choices for general, translation, and long-context work.",
        "caution_zh": "实用重评后代码仍仅 0.200；应按文本/长上下文优势使用。",
        "caution_en": "Code remains only 0.200 after practical regrading; use it for its text and long-context strengths.",
    },
    "glm-ocr:latest": {
        "use_zh": "可作为 OCR 语义识别研究对象，但必须配合去重和终止控制。",
        "use_en": "Useful for OCR semantic-recognition research with explicit deduplication and termination control.",
        "caution_zh": "语义分 0.810，但 10/10 输出截断、完成率 0%；不能按 0.810 当作可交付 OCR。",
        "caution_en": "Semantic score is 0.810, but all 10 outputs truncated and completion is 0%; this is not deliverable OCR.",
    },
    "granite4.1-guardian:8b": {
        "use_zh": "当前安全输入/输出分类的首选专用模型。",
        "use_en": "Current first choice for dedicated input/output safety classification.",
        "caution_zh": "只应用于安全判定，不应当作聊天模型。",
        "caution_en": "Use only as a safety judge, not as a chat model.",
    },
    "granite4.1:8b": {
        "use_zh": "稳定的多语言通用助手与企业文本任务候选。",
        "use_en": "Stable multilingual general assistant and enterprise-text candidate.",
        "caution_zh": "代码与工具表现中等，不是本机这两项的第一选择。",
        "caution_en": "Code and tools are mid-tier rather than best-in-class locally.",
    },
    "granite4:7b-a1b-h": {
        "use_zh": "速度优先的代码、翻译和工具调用候选。",
        "use_en": "Speed-oriented candidate for code, translation, and tool use.",
        "caution_zh": "实用 Core 为 0.702，但精确上游制品映射仍需确认。",
        "caution_en": "Practical Core is 0.702, but the exact upstream artifact mapping remains uncertain.",
    },
    "hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M": {
        "use_zh": "轻量文档视觉集成实验和翻译。",
        "use_en": "Lightweight document-vision integration experiments and translation.",
        "caution_zh": "视觉 0.875、OCR 0.370；视觉选择题改善明显，但 OCR 仍不可靠。",
        "caution_en": "Vision is 0.875 and OCR 0.370; visual fixtures improved, but OCR remains unreliable.",
    },
    "hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M": {
        "use_zh": "当前最适合作为默认本地通用/Agent 基线的模型。",
        "use_en": "The strongest current default for the local general/agent baseline.",
        "caution_zh": "长上下文实用分 1.000，但只有 4 条夹具且仍有 2 次截断。",
        "caution_en": "Long-context practical score is 1.000 on only four fixtures, with two truncations still recorded.",
    },
    "hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M": {
        "use_zh": "推理、通用与医疗文本的稳健对照模型。",
        "use_en": "A solid comparison model for reasoning, general, and medical text tasks.",
        "caution_zh": "代码为 0.500，且性能慢于若干 4B/混合架构模型。",
        "caution_en": "Code is 0.500 and it is slower than several 4B or hybrid alternatives.",
    },
    "hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL": {
        "use_zh": "小体积、快速翻译和轻量文本处理。",
        "use_en": "Small, fast model for translation and lightweight text processing.",
        "caution_zh": "核心、代码和工具表现弱，不宜承担复杂 Agent 工作。",
        "caution_en": "Weak core, code, and tools performance; avoid complex agent work.",
    },
    "huggingface.co/llmware/phi-4-mini-gguf:latest": {
        "use_zh": "低占用普通问答和翻译备选。",
        "use_en": "Low-footprint fallback for ordinary Q&A and translation.",
        "caution_zh": "代码 0.315、工具 0.477，复杂任务仍需强校验。",
        "caution_en": "Code 0.315 and Tools 0.477 still require strong validation on complex work.",
    },
    "huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest": {
        "use_zh": "离线推理或代码草案，适合允许失败重试的研究场景。",
        "use_en": "Offline reasoning or code drafts where research workflows tolerate failures.",
        "caution_zh": "实用 Core 仅 0.429，且原运行仍保留较多超时、异常与截断证据。",
        "caution_en": "Practical Core is only 0.429, with substantial timeout, anomaly, and truncation evidence retained.",
    },
    "kaelri/hy-mt2:7b-q4_K_M": {
        "use_zh": "专用翻译对照模型。",
        "use_en": "Dedicated translation comparison model.",
        "caution_zh": "翻译 0.800，低于本轮多个通用模型；不要外推到其他能力。",
        "caution_en": "Translation 0.800 trails several general models here; do not extrapolate to other capabilities.",
    },
    "lfm2.5:8b": {
        "use_zh": "速度优先的工具调用与推理候选。",
        "use_en": "Speed-first candidate for tool use and reasoning.",
        "caution_zh": "实用 Core 0.838、Tools 0.909，但仍需用更大题集验证泛化。",
        "caution_en": "Practical Core 0.838 and Tools 0.909 are promising, but broader fixtures are needed for generalization.",
    },
    "llama3.2:3b": {
        "use_zh": "轻量代码、工具调用和多语言文本。",
        "use_en": "Lightweight code, tool use, and multilingual text work.",
        "caution_zh": "实用 Core 0.748；复杂指令仍应结合工具与代码结果复核。",
        "caution_en": "Practical Core is 0.748; complex instructions still need validation against tool and code behavior.",
    },
    "medgemma1.5:4b": {
        "use_zh": "仅用于医疗模型集成诊断和未来定向补测。",
        "use_en": "Use only for medical-model integration diagnosis and future targeted retesting.",
        "caution_zh": "医疗 0.717、OCR 0.488；题量很小，绝不可用于真实医疗决策。",
        "caution_en": "Medical is 0.717 and OCR 0.488 on small fixtures; never use this for real clinical decisions.",
    },
    "minicpm-v4.6:latest": {
        "use_zh": "极快的翻译和轻量文本候选。",
        "use_en": "Extremely fast candidate for translation and lightweight text.",
        "caution_zh": "视觉 0.750、OCR 0.463，但本地参数元数据仍存在身份异常。",
        "caution_en": "Vision is 0.750 and OCR 0.463, but local parameter metadata still has identity anomalies.",
    },
    "ministral-3:8b": {
        "use_zh": "均衡的多语言、代码、工具和多模态候选。",
        "use_en": "Balanced multilingual, code, tool, and multimodal candidate.",
        "caution_zh": "视觉为 0.750，仍受 8 条小型夹具限制，速度也不占优。",
        "caution_en": "Vision is 0.750 on only eight fixtures, and speed is not a strength.",
    },
    "mistral:7b": {
        "use_zh": "稳定的传统 7B 多语言基线。",
        "use_en": "Stable traditional 7B multilingual baseline.",
        "caution_zh": "工具 0.767、长上下文 0.750；仍不是当前各赛道首选。",
        "caution_en": "Tools 0.767 and Long Context 0.750 are useful but not current track leaders.",
    },
    "nemotron-3-nano:4b": {
        "use_zh": "4B 级通用、医疗文本和中速 Agent 任务的优先候选。",
        "use_en": "Priority 4B candidate for general, medical-text, and medium-speed agent tasks.",
        "caution_zh": "翻译较弱且出现 1 次未知工具调用；医疗结果不代表临床安全。",
        "caution_en": "Translation is weaker and one unknown tool call occurred; medical results do not imply clinical safety.",
    },
    "olmo-3:7b-instruct": {
        "use_zh": "开放研究、通用文本和翻译的可解释对照。",
        "use_en": "Transparent comparison model for open research, general text, and translation.",
        "caution_zh": "代码 0.400，综合表现仍未达到本轮最强组。",
        "caution_en": "Code 0.400 and the overall profile still trail the strongest group.",
    },
    "olmo-3:7b-think": {
        "use_zh": "允许较长等待时的代码与推理研究。",
        "use_en": "Code and reasoning research when longer waits are acceptable.",
        "caution_zh": "宽松恢复后仍有 2 次 final 前截断和 1 次超时，不适合时间敏感交互。",
        "caution_en": "After recovery it still has two before-final truncations and one timeout, so it is unsuitable for latency-sensitive interaction.",
    },
    "openbmb/minicpm5:Q4_K_M": {
        "use_zh": "超轻量、极高吞吐的代码和翻译候选。",
        "use_en": "Ultra-light, very high-throughput candidate for code and translation.",
        "caution_zh": "实用重评表现明显改善，但仍有 2 次截断；超轻量优势不等于复杂任务可靠性。",
        "caution_en": "Practical regrading improves its profile, but two truncations remain; tiny size does not imply complex-task reliability.",
    },
    "ornith:9b": {
        "use_zh": "代码、通用和翻译任务的强力本地候选。",
        "use_en": "Strong local candidate for code, general, and translation tasks.",
        "caution_zh": "推理实用分 0.800，但尚未匹配到可信的精确官方模型卡。",
        "caution_en": "Practical Reasoning is 0.800, but no authoritative exact model card was matched.",
    },
    "phi4-mini-reasoning:latest": {
        "use_zh": "数学推理实验和轻量离线分析。",
        "use_en": "Mathematical reasoning experiments and lightweight offline analysis.",
        "caution_zh": "仍保留多次截断证据；实用分改善不等于时间敏感任务稳定。",
        "caution_en": "Multiple truncations remain; improved practical scores do not imply latency-sensitive stability.",
    },
    "phi4-mini:latest": {
        "use_zh": "快速普通文本与翻译备选。",
        "use_en": "Fast fallback for ordinary text and translation.",
        "caution_zh": "核心 0.611、代码 0.240、工具 0.477，复杂 Agent 能力有限。",
        "caution_en": "Core 0.611, Code 0.240, and Tools 0.477 limit complex agent use.",
    },
    "qwen3-embedding:latest": {
        "use_zh": "当前本地语义检索和向量嵌入的明确首选。",
        "use_en": "Clear current choice for local semantic retrieval and embeddings.",
        "caution_zh": "小型夹具 1.000 不等于复现官方 MTEB；不能用于文本生成。",
        "caution_en": "A perfect small-fixture score does not reproduce MTEB and the model is not for text generation.",
    },
    "qwen3-vl:8b": {
        "use_zh": "当前代码、工具与视觉最均衡的多模态候选。",
        "use_en": "The strongest current balance across code, tools, and vision.",
        "caution_zh": "仍有 1 次超时和 1 次截断；视觉 1.000 只代表 8 条小型夹具。",
        "caution_en": "One timeout and one truncation remain; Vision 1.000 covers only eight small fixtures.",
    },
    "qwen3.5:4b": {
        "use_zh": "4B 级通用、工具和轻量多模态候选。",
        "use_en": "4B-class candidate for general, tools, and lightweight multimodal work.",
        "caution_zh": "定向恢复选用了 14 条改善结果，但仍有 2 次 final 前截断；长输出需控制。",
        "caution_en": "Targeted recovery selected 14 improved results, but two before-final truncations remain; long outputs still need control.",
    },
    "qwen3.5:9b": {
        "use_zh": "通用和长上下文任务的高质量候选。",
        "use_en": "High-quality candidate for general and long-context tasks.",
        "caution_zh": "9 条恢复结果全部形成可评分输出；代码 0.410 仍弱于同级代码候选。",
        "caution_en": "All nine recovery items became scoreable, but Code 0.410 still trails peer code candidates.",
    },
    "rnj-1:latest": {
        "use_zh": "响应快、适合代码、STEM 和翻译的实用模型。",
        "use_en": "Responsive practical model for code, STEM, and translation.",
        "caution_zh": "实用 Core 0.829，但仍需强提示和结果校验。",
        "caution_en": "Practical Core is 0.829, but strong prompting and validation remain necessary.",
    },
    "shieldgemma:2b": {
        "use_zh": "资源较低时的安全内容初筛。",
        "use_en": "Low-resource first-pass safety screening.",
        "caution_zh": "安全综合分 0.708，低于 Granite Guardian；关键场景需复核。",
        "caution_en": "Safety composite is 0.708, below Granite Guardian; review high-impact decisions.",
    },
    "smollm2:1.7b": {
        "use_zh": "低资源文本生成、翻译和简单代码草案。",
        "use_en": "Low-resource text generation, translation, and simple code drafts.",
        "caution_zh": "工具恢复明显改善，但仍有 2 次工具循环上限；复杂 Agent 任务需限制轮次。",
        "caution_en": "Tool recovery improved substantially, but two loop-limit events remain; cap rounds for complex agent work.",
    },
    "starcoder2:7b": {
        "use_zh": "仅在专门的代码补全/FIM 流程中继续研究。",
        "use_en": "Continue only in a dedicated code-completion or FIM workflow.",
        "caution_zh": "它是基础补全模型，RC1 指令式纯函数代码得分为 0，当前比较并不匹配其原生用途。",
        "caution_en": "It is a base completion model; RC1 instruction-style pure-function code scored 0 and does not match its native use.",
    },
    "translategemma:latest": {
        "use_zh": "稳定的专用翻译模型和翻译质量对照。",
        "use_en": "Stable dedicated translation model and translation-quality comparator.",
        "caution_zh": "OCR 0.603 仍非其原生定位；不要外推为通用聊天或文档模型。",
        "caution_en": "OCR 0.603 is outside its native role; do not extrapolate to general chat or document understanding.",
    },
}


def read_csv(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def short_name(name: str) -> str:
    replacements = {
        "hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M": "Qwen3-8B Q4",
        "hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M": "Falcon-H1R-7B",
        "huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest": "DS-R1-Qwen3-8B",
        "hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M": "Granite Vision 4B",
        "hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL": "SmolLM3-3B",
        "huggingface.co/llmware/phi-4-mini-gguf:latest": "Phi-4-mini GGUF",
        "openbmb/minicpm5:Q4_K_M": "MiniCPM5-1B",
    }
    return replacements.get(name, name.replace(":latest", ""))


def build_assessments() -> list[dict[str, Any]]:
    inventory = {
        row["exact_name"]: row for row in read_csv("inventory/model_inventory.csv")
        if row["local_or_cloud"] == "local"
    }
    official = {row["model"]: row for row in read_csv("inventory/official_model_references.csv")}
    performance = {
        row["model"]: row for row in read_csv("public_results/rc1_performance.csv")
        if row["scope"] == "local"
    }
    score_rows: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in read_csv("public_results/rc1_practical_track_scores.csv"):
        if row["scope"] == "local_practical":
            score_rows[row["model"]][row["track"]] = row
    strict_score_rows: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in read_csv("public_results/rc1_track_scores.csv"):
        if row["scope"] == "local":
            strict_score_rows[row["model"]][row["track"]] = row
    failures: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in read_csv("public_results/rc1_practical_failure_counts.csv"):
        if row["scope"] == "local_practical":
            failures[row["model"]][row["category"]] += int(row["count"])

    missing_notes = sorted(set(inventory) - set(NOTES))
    extra_notes = sorted(set(NOTES) - set(inventory))
    if missing_notes or extra_notes:
        raise RuntimeError(f"assessment coverage mismatch missing={missing_notes} extra={extra_notes}")

    assessments: list[dict[str, Any]] = []
    for model in sorted(inventory):
        inv = inventory[model]
        ref = official.get(model, {})
        perf = performance.get(model, {})
        role_zh, role_en = ROLE_OVERRIDES.get(
            model,
            ROLE_LABELS.get(inv["apparent_specialist_role"], ROLE_LABELS[""]),
        )
        scores = {
            track: {
                "mean": float(row["mean_score_0_to_1"]),
                "records": int(row["records"]),
                "scored_records": int(row["scored_records"]),
                "coverage": float(row["coverage"]),
                "completion_rate": float(row["completion_rate"]),
                "completion_adjusted_mean": float(row["completion_adjusted_mean_0_to_1"]) if row["completion_adjusted_mean_0_to_1"] else None,
                "recovery_attempted": int(row["recovery_attempted"]),
                "recovery_selected": int(row["recovery_selected"]),
                "strict_mean": float(strict_score_rows[model][track]["mean_score_0_to_1"]) if track in strict_score_rows[model] and strict_score_rows[model][track]["mean_score_0_to_1"] else None,
            }
            for track, row in score_rows[model].items()
            if row["mean_score_0_to_1"] != ""
        }
        assessment = {
            "model": model,
            "short_name": short_name(model),
            "digest": inv["digest"],
            "parameter_size": inv["parameter_size"],
            "quantization": inv["quantization"],
            "disk_size_gib": float(inv["disk_size_gib"]),
            "context_length": int(inv["context_length"] or 0),
            "capabilities": [item for item in inv["capabilities"].split(";") if item],
            "role": {"zh": role_zh, "en": role_en},
            "official_model": ref.get("official_model") or "UNVERIFIED",
            "official_source_url": ref.get("official_source_url") or None,
            "publisher_claim_summary": ref.get("publisher_claim_summary") or "No authoritative exact model card was matched.",
            "match_confidence": ref.get("match_confidence") or "UNVERIFIED",
            "scores": scores,
            "score_basis": "practical-regrade-1 with selected rc1-relaxed-recovery-v1 evidence",
            "performance": {
                "wall_seconds_p50": float(perf["wall_seconds_p50"]) if perf.get("wall_seconds_p50") else None,
                "output_tokens_per_second_mean": float(perf["output_tokens_per_second_mean"]) if perf.get("output_tokens_per_second_mean") else None,
            },
            "failures": dict(sorted(failures[model].items())),
            "recommendation": {"zh": NOTES[model]["use_zh"], "en": NOTES[model]["use_en"]},
            "caution": {"zh": NOTES[model]["caution_zh"], "en": NOTES[model]["caution_en"]},
        }
        assessments.append(assessment)
    return assessments


def score_text(model: dict[str, Any], language: str) -> str:
    label_index = 0 if language == "zh" else 1
    ranked = sorted(model["scores"].items(), key=lambda item: (-item[1]["mean"], TRACKS.index(item[0]) if item[0] in TRACKS else 99))
    shown = ranked[:4]
    if not shown:
        return "无评分赛道" if language == "zh" else "No scored track"
    parts = []
    for track, value in shown:
        part = f"{TRACK_LABELS[track][label_index]} {value['mean']:.3f}"
        if value.get("completion_rate", 1.0) < 1.0:
            suffix = f"完成 {value['completion_rate']:.0%}" if language == "zh" else f"completion {value['completion_rate']:.0%}"
            part += f"（{suffix}）" if language == "zh" else f" ({suffix})"
        parts.append(part)
    return "；".join(parts) if language == "zh" else "; ".join(parts)


def source_link(model: dict[str, Any], language: str) -> str:
    if model["official_source_url"]:
        label = "官方来源" if language == "zh" else "Official source"
        return f"[{label}]({model['official_source_url']})"
    return "未确认" if language == "zh" else "Unverified"


def write_charts(assessments: list[dict[str, Any]]) -> None:
    out = ROOT / "docs" / "assets"
    out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 13, "axes.labelsize": 10})
    palette = {"blue": "#3066BE", "gold": "#D79B32", "ink": "#18212F", "grid": "#D9DEE7", "soft": "#E9EEF6"}

    core = [m for m in assessments if "core" in m["scores"]]
    core.sort(key=lambda m: m["scores"]["core"]["mean"], reverse=True)
    top = list(reversed(core[:10]))
    fig, ax = plt.subplots(figsize=(10, 6.2), dpi=180)
    bars = ax.barh([m["short_name"] for m in top], [m["scores"]["core"]["mean"] for m in top], color=palette["blue"], edgecolor=palette["ink"], linewidth=.45)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Mean score (0–1), 24 RC1 core records per model")
    ax.set_title("RC1 local core score — top 10 models", loc="left", weight="bold")
    ax.grid(axis="x", color=palette["grid"], linewidth=.7)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.bar_label(bars, fmt="%.3f", padding=4, color=palette["ink"], fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "rc1_core_top10.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    points = [m for m in core if m["performance"]["output_tokens_per_second_mean"] is not None]
    fig, ax = plt.subplots(figsize=(10, 6.2), dpi=180)
    xs = [m["performance"]["output_tokens_per_second_mean"] for m in points]
    ys = [m["scores"]["core"]["mean"] for m in points]
    sizes = [55 + m["disk_size_gib"] * 11 for m in points]
    scatter = ax.scatter(xs, ys, s=sizes, c=ys, cmap="Blues", vmin=0, vmax=1, edgecolor=palette["ink"], linewidth=.45, alpha=.9)
    labels = {
        "hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M", "gemma4:e4b", "qwen3.5:9b",
        "nemotron-3-nano:4b", "granite4:7b-a1b-h", "lfm2.5:8b", "openbmb/minicpm5:Q4_K_M",
    }
    for model in points:
        if model["model"] in labels:
            x_value = model["performance"]["output_tokens_per_second_mean"]
            x_offset = -5 if x_value > 225 else 5
            alignment = "right" if x_offset < 0 else "left"
            ax.annotate(
                model["short_name"],
                (x_value, model["scores"]["core"]["mean"]),
                xytext=(x_offset, 5),
                textcoords="offset points",
                fontsize=7.5,
                ha=alignment,
            )
    ax.set_xlabel("Mean output tokens/s (performance fixture)")
    ax.set_ylabel("RC1 core mean score (0–1)")
    ax.set_title("Local speed–core trade-off", loc="left", weight="bold")
    ax.grid(color=palette["grid"], linewidth=.7)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    colorbar = fig.colorbar(scatter, ax=ax, pad=.02)
    colorbar.set_label("Core mean")
    fig.tight_layout()
    fig.savefig(out / "rc1_speed_core_tradeoff.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    issue_rows = []
    for model in assessments:
        trunc = sum(value for key, value in model["failures"].items() if "trunc" in key)
        timeout = sum(value for key, value in model["failures"].items() if "timeout" in key)
        other = sum(value for key, value in model["failures"].items() if "trunc" not in key and "timeout" not in key)
        if trunc + timeout + other:
            issue_rows.append((model, trunc, timeout, other))
    issue_rows.sort(key=lambda row: row[1] + row[2] + row[3], reverse=True)
    issue_rows = list(reversed(issue_rows[:10]))
    labels_y = [row[0]["short_name"] for row in issue_rows]
    truncs = [row[1] for row in issue_rows]
    timeouts = [row[2] for row in issue_rows]
    others = [row[3] for row in issue_rows]
    fig, ax = plt.subplots(figsize=(10, 6.2), dpi=180)
    ax.barh(labels_y, truncs, color=palette["blue"], label="Truncation-related")
    ax.barh(labels_y, timeouts, left=truncs, color=palette["gold"], label="Absolute timeout")
    ax.barh(labels_y, others, left=[a+b for a,b in zip(truncs,timeouts)], color="#8894A7", label="Other runtime/tool")
    ax.set_xlabel("Recorded events")
    ax.set_title("Models with the most recorded runtime issues", loc="left", weight="bold")
    ax.grid(axis="x", color=palette["grid"], linewidth=.7)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, ncol=3, loc="lower right")
    fig.tight_layout()
    fig.savefig(out / "rc1_runtime_issues.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def model_table(assessments: list[dict[str, Any]], language: str) -> list[str]:
    if language == "zh":
        lines = [
            "| 模型 | 规模/量化 | 能力预期 | 本机实际表现 | 推荐用途 | 注意事项 | 来源 |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    else:
        lines = [
            "| Model | Size / quant | Expected role | Observed locally | Recommended use | Caution | Source |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    for model in assessments:
        expected = model["role"][language]
        fields = [
            f"`{model['model']}`",
            f"{model['parameter_size']} / {model['quantization']}",
            expected,
            score_text(model, language),
            model["recommendation"][language],
            model["caution"][language],
            source_link(model, language),
        ]
        lines.append("| " + " | ".join(field.replace("|", "\\|") for field in fields) + " |")
    return lines


def report_zh(assessments: list[dict[str, Any]]) -> str:
    lines = [
        "# SummerTestModel Benchmark 1.0-rc1 阶段最终报告",
        "",
        "[中文] · [English](final_report.en.md)",
        "",
        "## 技术摘要：这次 RC1 应当成为后续增量评测的唯一基线",
        "",
        "本阶段完成了 39/39 个本地模型、1,938 道适用任务的正式执行，并在独立范围内完成 2 个云端模型的 142 条参考记录。随后对全部 1,938 条 raw 做了实用型离线重评，并只针对 8 个模型的 50 条超时、截断或工具异常记录执行一次宽松恢复；39 条恢复证据被选入实用快照，6 条仍无可评分 final。严格基线及其 raw 完全保留，没有缺失 raw、重复 inference key、评分错误或基础设施缺口。",
        "",
        "这份结果最有价值的不是产生一个“万能总榜”，而是建立了以后可以持续追加模型的规范：固定任务与评分器、按能力分赛道、记录 digest/量化/运行环境、基础设施失败不计能力 0 分、评分更新优先离线重评。当前最实用的结论是：",
        "",
        "- **默认本地通用/Agent 参考**：`Qwen3-8B Q4_K_M` 与 `qwen3-vl:8b`；两者 Core 都为 0.879、Tools 都为 0.909、Long Context 都为 1.000，后者在本轮 Code 0.890、Vision 1.000。",
        "- **通用与长上下文**：`gemma4:e4b`、`qwen3.5:9b` 和上述两个 Qwen；这些模型在实用评分下长上下文均达到 1.000，但题量只有 4 条，不能外推为极限上下文能力。",
        "- **速度优先**：`granite4:7b-a1b-h`、`lfm2.5:8b`、`MiniCPM5-1B`；高吞吐不等于高通用分，应按工具/代码/翻译等具体用途使用。",
        "- **代码**：`olmo-3:7b-think` 0.900、`qwen3-vl:8b` 0.890、`ornith:9b` 0.810、`deepseek-r1:8b` 0.775；必须与各自超时、截断和来源风险一起阅读。",
        "- **专用模型**：嵌入选 `qwen3-embedding`，安全分类选 `Granite Guardian`。OCR 中 `GLM-OCR` 语义分 0.810 但完成率为 0%，`DeepSeek-OCR` 0.792 且完成率 100%，两者不能只按分数排序。",
        "- **医疗**：`nemotron-3-nano:4b`、`qwen3.5:4b` 和 `qwen3.5:9b` 在当前夹具均为 0.800；这不是临床有效性或安全性证明。",
        "",
        "![RC1 本地核心赛道前十名](assets/rc1_core_top10.png)",
        "",
        "图 1：39 个本地模型中具有 Core 记录的模型比较；每个模型 24 条 Core 记录，分数为 0–1 的赛道均值。",
        "",
        "## 为什么这样设计：测“这台电脑上的可用性”，而不是复制厂商排行榜",
        "",
        "1. **本地范围明确**：正式基线只包含本机安装且总参数不超过约 10B 的本地模型。云端模型只作独立参考，避免把硬件约束和服务端能力混成一个榜。",
        "2. **赛道独立**：Core、Reasoning、Code、Translation、Tools、Vision、OCR、Long Context、Embedding、Safety、Medical、Performance 分开解释；没有 universal overall score。否则专用模型会因不适用任务被错误惩罚。",
        "3. **两层运行边界**：严格基线保留原 profile 边界；实用恢复只对预先列出的 50 条异常记录使用一次宽松预算，并明确标注，绝不静默替换原证据。",
        "4. **不使用格式约束解码**：题目要求 JSON 时也不启用 `format=json`，因为协议遵循本身就是被测能力。",
        "5. **Thinking 与 final 分离**：普通赛道不把思维链拼入答案评分；Reasoning 只对元数据声明 thinking 的模型启用。",
        "6. **证据分层**：raw inference、normalized interpretation、scorer output、report/leaderboard 四层分离，因此修改评分器不要求重新推理。",
        "7. **失败分层**：网络/服务不可用与模型错误答案分开；transport failure 最多重试一次，语义错误、超时、截断和 scorer failure 不重试推理。",
        "8. **模型身份稳定**：唯一键包含 benchmark version、task manifest hash、model digest、profile 和 task ID；同名但 digest 改变会成为新 revision。",
        "",
        "## 数据、指标与比较边界",
        "",
        "| 项目 | 定义 |",
        "| --- | --- |",
        "| 本地样本 | 39 个已安装本地模型；每个模型只运行适用赛道 |",
        "| 任务记录 | 1,938 条本地派生记录；对应 1,938 份本地不可变 raw |",
        "| 严格分数 | 原 RC1 scorer 的固定边界结果，完整保留用于复核 |",
        "| 实用分数 | 对既有 raw 离线重评；仅在恢复产生可评分或更高分结果时选择恢复证据，仍按赛道独立展示 |",
        "| Coverage | 已评分记录 / 当前模型在该赛道的记录数，不表示全模型覆盖 |",
        "| Performance | Ollama 提供的 token/duration 与 wall time；不增加能力得分 |",
        "| Runtime anomaly | 流中断、工具循环、超时、截断等执行表现；与基础设施故障分开 |",
        "| 官方比较 | 仅用于解释模型预期定位；未复现相同数据集、精度、prompt 与 runtime 时不做数值等价比较 |",
        "",
        "运行环境为 Windows 11、Intel i5-13500HX、31.8 GiB RAM、RTX 4060 Laptop 8 GiB VRAM。严格基线记录 Ollama 0.32.6，定向恢复记录 0.32.9；项目把版本当作环境元数据，不把某个 patch 版本当作永久门槛。",
        "",
        "## 主要结果：质量、速度与稳定性必须一起看",
        "",
        "### 1. 均衡能力比单项第一更适合作为默认模型",
        "",
        "实用评分下 `Qwen3-8B Q4_K_M` 与 `qwen3-vl:8b` 都达到 Core 0.879、Tools 0.909、Long Context 1.000；前者是稳定的纯文本参考，后者在 Code 0.890 和 Vision 1.000 更突出。`gemma4:e4b` 的 Core 0.879、Translation/Long Context 1.000 也很强，但 Code 只有 0.200。不存在脱离工作负载的唯一冠军。",
        "",
        "### 2. 高吞吐与通用能力存在明显取舍",
        "",
        "![本地速度与 Core 得分关系](assets/rc1_speed_core_tradeoff.png)",
        "",
        "图 2：只有同时具备 Core 与 performance 记录的本地生成模型进入图中；气泡大小近似模型文件大小。Performance 是描述指标，不计能力分。",
        "",
        "`MiniCPM5-1B`、`LFM2.5` 和 `Granite 4 7B-A1B` 吞吐很高；实用重评改善了它们的语义/协议归因，但速度仍然不进入能力分。实际部署应先确定任务，再在同一赛道候选中比较吞吐，而不是先做一个速度总榜。",
        "",
        "### 3. 推理模型最容易暴露“会想但来不及给 final”的问题",
        "",
        "`DeepSeek-R1-0528-Qwen3-8B`、`DeepSeek-R1 8B`、`OLMo Think` 和 `Phi-4-mini-reasoning` 都出现较多截断或 final 前终止。RC1 的 practical-local boundary 使这些现象成为可用性证据：模型可能生成了较长 thinking，但在预算内没有形成可评分 final。",
        "",
        "![运行问题较多的模型](assets/rc1_runtime_issues.png)",
        "",
        "图 3：按记录事件数展示问题较多的模型；这些事件不等价于基础设施失败，也不自动进入能力分母。",
        "",
        "### 4. 专用模型必须按原生用途解释",
        "",
        "`qwen3-embedding` 在 12 个小型检索查询上为 1.000，但不能声称复现 MTEB。`Granite Guardian` 在 20 个安全样本上为 1.000，适合安全判定而不是聊天。`GLM-OCR` 的语义均值 0.810 与完成率 0% 同时成立，正说明语义正确、重复退化和完成状态必须分开。`StarCoder2` 的基础补全定位也不能直接等同于指令式纯函数能力。",
        "",
        "## 按用途推荐",
        "",
        "| 用途 | 首选 | 备选 | 为什么 |",
        "| --- | --- | --- | --- |",
        "| 默认本地助手 | Qwen3-8B Q4 | Qwen3-VL 8B、Gemma4 E4B、Nemotron 4B | Core、工具、翻译与长上下文均衡 |",
        "| 代码 | OLMo Think / Qwen3-VL 8B | Ornith 9B、DeepSeek-R1 8B、MiniCPM5 | 实用 Code 0.900 / 0.890；需结合稳定性和来源 |",
        "| 工具调用 | Qwen3-8B / Qwen3-VL / LFM2.5 | Falcon H1R、Gemma4、Qwen3.5 | 头部约 0.90，需同时看循环/未知工具事件 |",
        "| 翻译 | Gemma4 / Qwen3-8B | Granite4.1、Ministral3、TranslateGemma | 本轮翻译 0.967–1.000；专用模型用于对照 |",
        "| 长上下文 | Qwen3-8B / Qwen3-VL / Gemma4 / Qwen3.5 | 多个 1.000 候选 | 仅 4 条夹具，不代表 128K/1M 极限 |",
        "| 低资源/高吞吐 | MiniCPM5 1B | Granite4 A1B、LFM2.5、SmolLM2 | 吞吐高，但通用能力不等价 |",
        "| 安全分类 | Granite Guardian 8B | ShieldGemma 2B | 1.000 对 0.708；后者更省资源 |",
        "| 嵌入检索 | Qwen3 Embedding | 暂无同类对照 | 12/12 小型检索夹具通过 |",
        "| OCR | DeepSeek OCR（实验） | GLM-OCR（语义实验）、Qwen3.5 / Qwen3-VL | 必须同时看语义分与完成率 |",
        "| 医疗文本 | Nemotron 4B / Qwen3.5（研究） | Falcon H1R / MedGemma | 仅代表当前夹具，不能替代医学验证 |",
        "",
        "## 逐模型：能力预期、实测与建议",
        "",
        "“能力预期”来自安装元数据和发布者模型卡映射；“本机实际表现”只取本次 RC1；“推荐用途/注意事项”是基于二者的项目决策建议，不是新增评分器或 retention 判定。",
        "",
    ]
    lines.extend(model_table(assessments, "zh"))
    lines.extend([
        "",
        "## 官方数据应该如何与本机结果对照",
        "",
        "官方 benchmark 说明模型在特定数据集、精度、模板、推理框架和硬件上的潜力；RC1 说明当前 Ollama 量化制品在这台电脑、这套 prompt 和时间边界下的可用性。二者回答的问题不同。可靠做法是：记录官方来源和预期生态位，观察本机是否出现方向性一致，再决定是否值得做同 benchmark 的复现实验。不要用 RC1 的 0.879 去与 MMLU、HumanEval、MTEB 或 OmniDocBench 百分数直接相减。",
        "",
        "已核对的关键官方定位包括 Qwen3 的 thinking/non-thinking 模式、Gemma4 的多模态/长上下文定位、Granite 4.1 的指令与工具能力、Granite Guardian 的安全判定用途；逐模型官方链接已放在上表。`ornith:9b` 仍未匹配到可信的精确官方卡，应先解决 provenance 再作强结论。",
        "",
        "## 使用和解释时必须注意",
        "",
        "- 视觉/OCR 夹具较少；实用语义分更宽松，但必须和 completion/repetition 一起阅读。",
        "- Reasoning 的 thinking token 不进入普通答案 scorer；没有 final 的长 thinking 不能当作答对。",
        "- 代码仅测试受限纯函数，并经过 AST gate 与隔离子进程；不能代表完整软件工程 Agent。",
        "- Safety/Medical 是小型定向夹具。安全 1.000 或医疗领先都不能替代领域验证。",
        "- Performance 只在本机、当时后台负载和量化条件下可比；云端 wall time 与本地 tok/s 不混排。",
        "- 模型 digest、量化、模板、Ollama 版本改变时都应记录；版本变化本身不阻止增量测试，只有 digest 改变才是新 model revision。",
        "- 当前 retention 全部为 `UNASSESSED`。推荐用途不等于删除建议。",
        "",
        "## 以后新增模型的规范流程",
        "",
        "1. `ollama pull` 后先读取真实 metadata/digest，不按名字猜能力。",
        "2. 选择一个已有、能力相近的 reference assignment，只运行新模型的适用赛道。",
        "3. 每题开始、raw 完成、评分完成分别落盘；中断后 resume 自动跳过有效终态。",
        "4. 如 scorer 改进，优先使用已有 raw 离线重评，不重新调用模型。",
        "5. 生成新的 sanitized public result，并把新模型加入同一 RC1 赛道表；不要重跑原 39 个模型。",
        "6. 只有 benchmark major version 改变、推理行为重大变化或用户明确要求统一复测时，才考虑全量重跑。",
        "",
        "对应命令与限制见 [增量模型工作流](INCREMENTAL_MODELS.md)。",
        "",
        "## 限制、下一步问题与本阶段结论",
        "",
        "当前最重要的限制是题量仍紧凑，Vision/OCR/Medical 尤其偏实验性；官方 benchmark 尚未在相同精度和运行时下复现；不同模型的量化、模板和 thinking 实现也影响结果。下一阶段不应立即扩大为另一次 39 模型全量测试，而应在真实使用中偶尔加入新模型，并优先回答：新模型是否在明确生态位上超过当前参考、是否在相近资源下更稳定、官方优势是否能在 Ollama 路径复现。",
        "",
        "**本阶段的真正收获**是一个可持续系统，而不只是一次排行榜：RC1 已成为规范化基线，39 个本地模型的证据完整保存，评分与推理解耦，失败分类可解释，未来新增模型无需重跑全部历史模型。",
        "",
        "## 关键文件",
        "",
        "- [双语交互网站](https://summertestmodel-benchmark.walker-ethan.chatgpt.site)",
        "- [RC1 完整结果](rc1_results.md)",
        "- [实用重评逐赛道 CSV](../public_results/rc1_practical_track_scores.csv)",
        "- [50 条定向恢复对照](../public_results/rc1_practical_recovery_20260813.csv)",
        "- [严格基线逐赛道 CSV](../public_results/rc1_track_scores.csv)",
        "- [性能数据](../public_results/rc1_performance.csv)",
        "- [失败分类](rc1_failure_analysis.md)",
        "- [官方来源映射](../inventory/official_model_references.csv)",
        "- [机器环境](machine_profile.md)",
        "- [历史参考](legacy_history.md)",
        "",
        "本报告于 2026-08-14 更新：严格 RC1 基线保持不变，默认展示实用离线重评及被选中的定向恢复结果。网站和后续增量报告均从同一脱敏结构化数据生成。",
    ])
    return "\n".join(lines) + "\n"


def report_en(assessments: list[dict[str, Any]]) -> str:
    lines = [
        "# SummerTestModel Benchmark 1.0-rc1 Final Phase Report",
        "",
        "[中文](final_report.zh-CN.md) · [English]",
        "",
        "## Technical summary: RC1 should be the sole baseline for future incremental evaluation",
        "",
        "This phase completed all 39 selected local models across 1,938 applicable task records, plus a separate 142-record reference run for two cloud models. All 1,938 raw records were then regraded offline under the practical policy, and one relaxed recovery was limited to 50 timeout, truncation, or tool-anomaly items across eight models. Thirty-nine recovery results were selected into the practical snapshot; six items still lack a scoreable final. The strict baseline and raw evidence remain intact, with no missing raw, duplicate key, scoring error, or infrastructure gap.",
        "",
        "The main value is not a universal leaderboard. It is a sustainable protocol: frozen tasks and scorers, track-specific comparison, recorded digests/quantization/runtime, infrastructure failures separated from capability failures, and offline regrading by default. The most useful conclusions are:",
        "",
        "- **Default local general/agent references:** `Qwen3-8B Q4_K_M` and `qwen3-vl:8b`; both reach Core 0.879, Tools 0.909, and Long Context 1.000, while Qwen3-VL adds Code 0.890 and Vision 1.000.",
        "- **General and long-context work:** `gemma4:e4b`, `qwen3.5:9b`, and the two Qwen references; their Long Context means are 1.000 under practical scoring, but each has only four fixtures.",
        "- **Speed-first work:** `granite4:7b-a1b-h`, `lfm2.5:8b`, and `MiniCPM5-1B`; high throughput does not imply high general capability, so use them for specific tool/code/translation roles.",
        "- **Code:** `olmo-3:7b-think` 0.900, `qwen3-vl:8b` 0.890, `ornith:9b` 0.810, and `deepseek-r1:8b` 0.775; each must be read beside its timeout, truncation, and provenance evidence.",
        "- **Specialists:** use `qwen3-embedding` for embeddings and `Granite Guardian` for safety. `GLM-OCR` reaches semantic 0.810 but 0% completion, while `DeepSeek-OCR` reaches 0.792 with 100% completion; score alone is insufficient.",
        "- **Medical:** `nemotron-3-nano:4b`, `qwen3.5:4b`, and `qwen3.5:9b` each reach 0.800 on the current fixtures, which is not evidence of clinical validity or safety.",
        "",
        "![Top ten local RC1 core scores](assets/rc1_core_top10.png)",
        "",
        "Figure 1. Models with Core records; each has 24 RC1 Core records and the bar is the 0–1 within-track mean.",
        "",
        "## Why the benchmark is designed this way",
        "",
        "1. **Local scope is explicit.** The formal baseline contains installed local models around or below 10B total parameters. Cloud models are a separate reference so server-side capability is not mixed with local hardware constraints.",
        "2. **Tracks stay independent.** Core, Reasoning, Code, Translation, Tools, Vision, OCR, Long Context, Embedding, Safety, Medical, and Performance are interpreted separately. There is no universal overall score that penalizes specialists for inapplicable work.",
        "3. **Runtime evidence has two explicit layers.** The strict baseline preserves its original profile boundaries. A one-attempt relaxed budget applies only to the frozen 50-item recovery queue and never silently replaces original evidence.",
        "4. **No constrained decoding assistance.** Tasks that request JSON still do not use `format=json`; protocol adherence is part of the tested capability.",
        "5. **Thinking and final answers are separated.** Thinking is not concatenated into ordinary answers, and Reasoning only enables it for models whose metadata declares support.",
        "6. **Evidence is layered.** Immutable inference, normalized interpretation, scorer output, and reports are separate, so scorer improvements do not require new inference.",
        "7. **Failures are layered.** Network or service unavailability is distinct from a wrong answer. Transport errors receive at most one retry; semantic errors, timeout, truncation, and scorer failure do not trigger re-inference.",
        "8. **Identity is revision-safe.** Keys include benchmark version, task-manifest hash, model digest, profile, and task ID. A changed digest is a new model revision.",
        "",
        "## Data, metrics, and comparison boundaries",
        "",
        "| Item | Definition |",
        "| --- | --- |",
        "| Local cohort | 39 installed local models; each model runs only applicable tracks |",
        "| Task records | 1,938 local derived records mapped to 1,938 immutable local raw files |",
        "| Strict score | Original RC1 scorer result under the frozen runtime boundary, preserved for audit |",
        "| Practical score | Offline regrade of existing raw plus selected recovery evidence; tracks remain independent |",
        "| Coverage | Scored records divided by records for that model/track, not global inventory coverage |",
        "| Performance | Ollama token/duration fields and wall time; contributes no capability points |",
        "| Runtime anomaly | Stream interruption, tool loop, timeout, or truncation; distinct from infrastructure failure |",
        "| Publisher comparison | Context for expected role only unless dataset, precision, prompt, runtime, and scorer are reproduced |",
        "",
        "The machine is Windows 11 with an Intel i5-13500HX, 31.8 GiB RAM, and an RTX 4060 Laptop GPU with 8 GiB VRAM. The strict baseline recorded Ollama 0.32.6 and targeted recovery recorded 0.32.9. Patch versions are environment metadata, not permanent gates.",
        "",
        "## Quality, speed, and stability must be read together",
        "",
        "### 1. Balance matters more than winning one track",
        "",
        "Under practical scoring, `Qwen3-8B Q4_K_M` and `qwen3-vl:8b` both reach Core 0.879, Tools 0.909, and Long Context 1.000. Qwen3-8B is the stable text reference; Qwen3-VL adds Code 0.890 and Vision 1.000. `gemma4:e4b` also reaches Core 0.879 and Translation/Long Context 1.000, but Code is only 0.200. There is no workload-free winner.",
        "",
        "### 2. Throughput and general quality show a real trade-off",
        "",
        "![Local speed and Core trade-off](assets/rc1_speed_core_tradeoff.png)",
        "",
        "Figure 2. Local generation models with both Core and performance records; bubble size approximates model-file size. Performance is descriptive and contributes no capability score.",
        "",
        "`MiniCPM5-1B`, `LFM2.5`, and `Granite 4 7B-A1B` remain high-throughput choices. Practical regrading changes semantic/protocol attribution, but speed still contributes no capability points. Select candidates by workload first, then compare throughput within that workload.",
        "",
        "### 3. Reasoning models often think without producing a timely final answer",
        "",
        "`DeepSeek-R1-0528-Qwen3-8B`, `DeepSeek-R1 8B`, `OLMo Think`, and `Phi-4-mini-reasoning` accumulate truncation or before-final failures. Under the practical-local boundary, that is usability evidence: lengthy thinking does not count as a correct answer if no scoreable final arrives.",
        "",
        "![Models with the most runtime issues](assets/rc1_runtime_issues.png)",
        "",
        "Figure 3. Recorded issue events for the most affected models. These events are not equivalent to infrastructure outages and do not automatically enter capability denominators.",
        "",
        "### 4. Specialists must be interpreted in their native role",
        "",
        "`qwen3-embedding` scored 1.000 on 12 small retrieval queries, but this does not reproduce MTEB. `Granite Guardian` scored 1.000 on 20 safety samples and should be used as a judge, not a chat model. `GLM-OCR` simultaneously has semantic mean 0.810 and 0% completion, proving why semantic correctness, degeneration, and completion must remain separate. StarCoder2's base completion role also differs from instruction-style pure functions.",
        "",
        "## Recommendations by use case",
        "",
        "| Use case | First choice | Alternatives | Rationale |",
        "| --- | --- | --- | --- |",
        "| Default local assistant | Qwen3-8B Q4 | Qwen3-VL 8B, Gemma4 E4B, Nemotron 4B | Balanced Core, tools, translation, and context |",
        "| Code | OLMo Think / Qwen3-VL 8B | Ornith 9B, DeepSeek-R1 8B, MiniCPM5 | Practical Code 0.900 / 0.890; choose by stability and provenance |",
        "| Tool use | Qwen3-8B / Qwen3-VL / LFM2.5 | Falcon H1R, Gemma4, Qwen3.5 | Leaders are near 0.90; also inspect loop and unknown-tool events |",
        "| Translation | Gemma4 / Qwen3-8B | Granite4.1, Ministral3, TranslateGemma | Current translation means 0.967–1.000 |",
        "| Long context | Qwen3-8B / Qwen3-VL / Gemma4 / Qwen3.5 | Several 1.000 candidates | Only four fixtures; not a 128K/1M limit test |",
        "| Low-resource throughput | MiniCPM5 1B | Granite4 A1B, LFM2.5, SmolLM2 | Fast, but not equivalent in general quality |",
        "| Safety classification | Granite Guardian 8B | ShieldGemma 2B | 1.000 vs 0.708; Shield uses fewer resources |",
        "| Embedding retrieval | Qwen3 Embedding | No peer in current baseline | Passed all 12 small retrieval fixtures |",
        "| OCR | DeepSeek OCR (experimental) | GLM-OCR (semantic only), Qwen3.5 / Qwen3-VL | Read semantic score and completion together |",
        "| Medical text | Nemotron 4B / Qwen3.5 (research) | Falcon H1R / MedGemma | Fixture result only, not medical validation |",
        "",
        "## Every model: expectation, observed behavior, and recommendation",
        "",
        "Expected role comes from installed metadata and mapped publisher model cards. Observed behavior is RC1-only. Recommendations and cautions are project guidance, not a new scorer or retention decision.",
        "",
    ]
    lines.extend(model_table(assessments, "en"))
    lines.extend([
        "",
        "## How to compare publisher data with local results",
        "",
        "Publisher benchmarks describe potential under specific datasets, precision, templates, runtimes, and hardware. RC1 describes usability for the installed quantized artifact through Ollama on this machine. Use publisher evidence to establish expected role, inspect whether the local direction is consistent, and only then decide whether reproducing the exact official benchmark is worthwhile. Never subtract an RC1 mean such as 0.879 from MMLU, HumanEval, MTEB, or OmniDocBench percentages.",
        "",
        "Key verified positioning includes Qwen3 thinking/non-thinking operation, Gemma4 multimodal and long-context positioning, Granite 4.1 instruction/tool use, and Granite Guardian safety judging. Each model row links its mapped official source. `ornith:9b` still lacks a trustworthy exact model-card match, so provenance should be resolved before strong conclusions.",
        "",
        "## Operational cautions",
        "",
        "- Vision/OCR fixtures are small. Practical semantic scores are more permissive, but completion and repetition remain separate evidence.",
        "- Thinking tokens do not enter ordinary answer scoring; long reasoning without a final answer is not scored as correct.",
        "- Code covers restricted pure functions behind an AST gate and isolated child process, not full repository engineering.",
        "- Safety and Medical are small targeted fixtures; a perfect safety score or medical leader is not domain validation.",
        "- Performance is comparable only on this machine under the recorded quantization and background conditions. Cloud wall time and local tokens/s remain separate.",
        "- Digest, quantization, template, and Ollama version are recorded. Version change alone does not block incremental testing; a changed digest is a new model revision.",
        "- Retention remains `UNASSESSED`; use recommendations are not deletion decisions.",
        "",
        "## The normalized workflow for adding future models",
        "",
        "1. After `ollama pull`, inspect real metadata and digest instead of guessing from the name.",
        "2. Select an explicit comparable reference assignment and run only applicable frozen tracks for the new model.",
        "3. Persist task start, raw completion, and score completion separately; resume automatically skips valid terminal evidence.",
        "4. Regrade existing raw evidence offline when scorers improve; do not regenerate model answers.",
        "5. Export a new sanitized public result and append the new model to the same RC1 track tables without rerunning the original 39.",
        "6. Consider a full rerun only for a major benchmark version, material inference-behavior change, or explicit annual/unified refresh.",
        "",
        "See the [incremental model workflow](INCREMENTAL_MODELS.md) for commands and constraints.",
        "",
        "## Limitations, further questions, and phase conclusion",
        "",
        "The task set remains compact, with Vision/OCR/Medical especially experimental. Official benchmarks have not been reproduced with matching precision and runtime, and quantization, templates, and thinking implementations affect results. The next phase should not immediately rerun 39 models. It should add occasional new models and ask whether each one improves a defined niche at comparable resources, improves stability, or reproduces an official advantage through the Ollama path.",
        "",
        "**The real phase output is a sustainable system, not merely a leaderboard:** RC1 is the normalized baseline, all 39 local models have complete evidence, scoring is decoupled from inference, failures are interpretable, and new models can be added without rerunning the baseline.",
        "",
        "## Key artifacts",
        "",
        "- [Interactive bilingual website](https://summertestmodel-benchmark.walker-ethan.chatgpt.site)",
        "- [Full RC1 result report](rc1_results.md)",
        "- [Practical model-by-track rows](../public_results/rc1_practical_track_scores.csv)",
        "- [Fifty-item targeted recovery comparison](../public_results/rc1_practical_recovery_20260813.csv)",
        "- [Strict baseline model-by-track rows](../public_results/rc1_track_scores.csv)",
        "- [Performance data](../public_results/rc1_performance.csv)",
        "- [Failure analysis](rc1_failure_analysis.md)",
        "- [Official source mapping](../inventory/official_model_references.csv)",
        "- [Machine profile](machine_profile.md)",
        "- [Historical reference](legacy_history.md)",
        "",
        "Updated on 2026-08-14: the strict RC1 baseline remains unchanged, while the default presentation uses the practical offline regrade plus selected targeted recovery evidence. The website and future reports are generated from the same sanitized structured data.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    assessments = build_assessments()
    payload = {
        "benchmark_version": "1.0-rc1",
        "result_basis": "practical-regrade-1 with selected rc1-relaxed-recovery-v1 evidence",
        "strict_baseline_replaced": False,
        "published_snapshot": "2026-08-14",
        "models": assessments,
    }
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    (ROOT / "public_results" / "rc1_model_assessments.json").write_text(encoded, encoding="utf-8")
    (ROOT / "site" / "data" / "rc1_model_assessments.json").write_text(encoded, encoding="utf-8")
    write_charts(assessments)
    (ROOT / "docs" / "final_report.zh-CN.md").write_text(report_zh(assessments), encoding="utf-8")
    (ROOT / "docs" / "final_report.en.md").write_text(report_en(assessments), encoding="utf-8")
    print(json.dumps({"models": len(assessments), "reports": 2, "charts": 3}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
