"""Build a factual, non-ranking RC1 model execution plan from the frozen inventory."""
from __future__ import annotations
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKS = ["core", "reasoning", "code", "translation", "tools", "vision", "ocr", "long_context", "embedding", "safety", "medical", "performance"]

def params_b(value):
    if value is None: return None
    text = str(value).strip().upper().replace(",", "")
    if text in {"", "0", "UNKNOWN", "NULL"}: return None
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*([BMKT]?)", text)
    if not match: return None
    number, suffix = float(match.group(1)), match.group(2)
    if suffix == "B": return number
    if suffix == "M": return number / 1000
    if suffix == "K": return number / 1_000_000
    return number / 1_000_000_000 if number > 1_000_000 else number

def size_class(total):
    if total is None: return "unknown"
    if total <= 1: return "tiny"
    if total <= 3: return "small"
    if total <= 5: return "medium"
    if total <= 10: return "large_small"
    return "over_10b"

def main():
    inventory = json.loads((ROOT / "inventory/model_inventory.json").read_text(encoding="utf-8"))
    models, excluded = [], []
    for item in inventory["models"]:
        cloud = item.get("local_or_cloud") == "cloud"
        total = params_b(item.get("parameter_size"))
        if cloud:
            excluded.append(item["exact_name"])
            continue
        context = item.get("context_length")
        caps = list(item.get("capabilities") or [])
        models.append({
            "model": item["exact_name"], "tag": item.get("tag"), "digest": item.get("digest"), "local_or_cloud": "local",
            "candidate_status": "RETAINED_CANDIDATE", "formal_eligible": total is None or total <= 10,
            "total_params_b": total, "total_params_source": "inventory.parameter_size", "size_class": size_class(total),
            "disk_size_bytes": item.get("disk_size_bytes"), "quantization": item.get("quantization"), "family": item.get("family"), "architecture": item.get("architecture"),
            "active_params": item.get("active_params"), "effective_params": item.get("effective_params"), "architecture_notes": item.get("architecture_notes"),
            "declared_context": context, "verified_context_tiers": [tier for tier, minimum in (("8k", 8192), ("32k", 32768)) if isinstance(context, (int, float)) and context >= minimum],
            "metadata_capabilities": caps, "reasoning_allowed": "thinking" in caps,
            "retention_status": "UNASSESSED", "dominated_by": None, "dominance_evidence": None,
            "metadata_confidence": item.get("metadata_confidence"), "local_testability": item.get("local_testability")
        })
    output = {"schema_version": 1, "benchmark_version": "1.0-rc1", "selection_policy": {"local_only": True, "max_total_params_b": 10.0, "retain_all_local_candidates": True}, "track_ids": TRACKS, "final_track_task_assignments": "__PENDING_WEB_GPT_DECISION__", "models": models, "excluded_cloud_models": excluded, "counts": {"inventory_total": len(inventory["models"]), "local_candidates": len(models), "cloud_excluded": len(excluded), "formal_eligible_local": sum(m["formal_eligible"] for m in models)}}
    (ROOT / "config/model_execution_plan.rc1.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output["counts"], ensure_ascii=False))
if __name__ == "__main__": main()
