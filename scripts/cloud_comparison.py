"""Run a separate RC1 cloud reference comparison without altering the local baseline."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.executor_core import EvidenceStore, TERMINAL_INFERENCE, now
from scripts.luna_executor import doctor as luna_doctor, status as luna_status
from scripts.rc1_runner import DEFAULT_CONFIG, RC1ItemBuilder, _run_items, config_bundle

DEFAULT_PLAN = ROOT / "config" / "cloud_comparison_plan.rc1.json"
DEFAULT_RUN = ROOT / "private_runs" / "rc1_cloud_comparison_20260812"
DEFAULT_OUTPUT = ROOT / "public_results" / "rc1_cloud_comparison_20260812.jsonl"


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def atomic_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def api_json(base: str, endpoint: str, payload: dict[str, Any] | None = None) -> tuple[int | None, dict[str, Any]]:
    request = urllib.request.Request(
        base.rstrip("/") + endpoint,
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read()
            value = json.loads(body.decode("utf-8")) if body else {}
            return getattr(response, "status", 200), value if isinstance(value, dict) else {"value": value}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        try:
            value = json.loads(body)
        except json.JSONDecodeError:
            value = {"error": body[:500]}
        return exc.code, value if isinstance(value, dict) else {"value": value}
    except Exception as exc:
        return None, {"error": f"{type(exc).__name__}: {exc}"}


def approved_config(config_path: Path, run_dir: Path) -> Path:
    config = copy.deepcopy(read(config_path))
    config["calibration_approved"] = True
    config["output_dir"] = str(run_dir.relative_to(ROOT)).replace("\\", "/")
    output = run_dir / "approved_cloud_comparison_config.json"
    atomic_json(output, config)
    return output


def preflight(config_path: Path, plan_path: Path, run_dir: Path) -> dict[str, Any]:
    bundle = config_bundle(config_path)
    plan = read(plan_path)
    base = str(bundle["config"].get("ollama_api") or "http://127.0.0.1:11434")
    approved = approved_config(config_path, run_dir)
    doctor_result, doctor_checks = luna_doctor(approved)
    version_http, version = api_json(base, "/api/version")
    tags_http, tags = api_json(base, "/api/tags")
    tag_rows = {row.get("name"): row for row in tags.get("models", [])}
    inventory = {row["exact_name"]: row for row in bundle["inventory"]["models"]}
    model_rows: list[dict[str, Any]] = []
    for planned in plan["models"]:
        model = planned["model"]
        show_http, show = api_json(base, "/api/show", {"model": model})
        message = str(show.get("error") or show.get("message") or "")
        live_capabilities = list(show.get("capabilities") or []) if show_http == 200 else []
        digest = (tag_rows.get(model) or {}).get("digest")
        if show_http == 200 and digest == planned["digest"] and set(planned.get("capabilities") or []).issubset(set(live_capabilities)):
            availability = "AVAILABLE"
        elif show_http == 410 and "retired" in message.casefold():
            availability = "RETIRED_HTTP_410"
        elif digest != planned["digest"]:
            availability = "DIGEST_MISMATCH"
        else:
            availability = "UNAVAILABLE"
        model_rows.append({
            "model": model,
            "planned_digest": planned["digest"],
            "live_digest": digest,
            "inventory_digest": (inventory.get(model) or {}).get("digest"),
            "show_http": show_http,
            "availability": availability,
            "capabilities": live_capabilities,
            "reference_model": planned.get("reference_model"),
            "detail": message,
        })
    result = {
        "status": "PASS" if doctor_result == "READY" and version_http == 200 and tags_http == 200 else "FAIL",
        "checked_at": now(),
        "scope": "cloud_reference_only",
        "benchmark_version": bundle["benchmark"]["benchmark_version"],
        "scorer_version": bundle["config"]["scorer_version"],
        "ollama_version": version.get("version"),
        "ollama_version_policy": "record_only_not_a_patch_version_gate",
        "doctor": doctor_result,
        "doctor_failures": [row for row in doctor_checks if row.get("status") != "PASS"],
        "models": model_rows,
        "available_models": sum(row["availability"] == "AVAILABLE" for row in model_rows),
        "retired_models": sum(row["availability"] == "RETIRED_HTTP_410" for row in model_rows),
        "local_baseline_impact": "none",
    }
    atomic_json(run_dir / "cloud_preflight.json", result)
    return result


def build_items(bundle: dict[str, Any], plan: dict[str, Any], preflight_result: dict[str, Any], selected_model: str | None) -> list[dict[str, Any]]:
    availability = {row["model"]: row["availability"] for row in preflight_result["models"]}
    frozen_rows = {row["model"]: row for row in bundle["plan"]["models"]}
    builder = RC1ItemBuilder(bundle)
    items: list[dict[str, Any]] = []
    for planned in plan["models"]:
        model = planned["model"]
        if selected_model and model != selected_model:
            continue
        if availability.get(model) != "AVAILABLE":
            continue
        reference = frozen_rows.get(planned.get("reference_model"))
        if not reference:
            raise ValueError(f"missing frozen capability-equivalent reference row: {model}")
        model_row = {"model": model, "digest": planned["digest"], "local_or_cloud": "cloud"}
        for task_id in reference.get("task_ids") or []:
            item = builder.build(model_row, task_id)
            item["comparison_scope"] = "cloud_reference_only"
            item["assignment_reference_model"] = planned["reference_model"]
            items.append(item)
    return items


def finalize(run_dir: Path, output: Path, preflight_result: dict[str, Any]) -> dict[str, Any]:
    state = EvidenceStore(run_dir).load_state()
    rows: list[dict[str, Any]] = []
    for logical, entry in (state.get("items") or {}).items():
        raw_path = run_dir / str(entry.get("raw_path")) if entry.get("raw_path") else None
        raw = read(raw_path) if raw_path and raw_path.is_file() else {}
        score_path = run_dir / "scores" / raw_path.parent.name / raw_path.name if raw_path else None
        score = read(score_path) if score_path and score_path.is_file() else None
        row = {
            "record_type": "task_result",
            "comparison_scope": "cloud_reference_only",
            "benchmark_version": raw.get("benchmark_version"),
            "task_manifest_hash": raw.get("task_manifest_hash"),
            "scorer_version": raw.get("scorer_version"),
            "ollama_version": raw.get("ollama_version"),
            "logical_key": logical,
            "model": raw.get("model"),
            "model_digest": raw.get("model_digest"),
            "task_id": raw.get("task_id"),
            "profile": raw.get("profile"),
            "inference_status": raw.get("inference_status"),
            "done_reason": raw.get("done_reason"),
            "termination_reason": raw.get("termination_reason"),
            "runtime_anomaly": raw.get("runtime_anomaly") is True,
            "terminal_record_seen": raw.get("terminal_record_seen"),
            "scoring_status": entry.get("scoring_status"),
            "timing": raw.get("timing", {}),
        }
        if score is not None:
            row["score"] = {
                key: value for key, value in score.items()
                if key not in {"logical_key", "attempt_id", "scored_at", "scorer_version"}
            }
        rows.append(row)
    for model in preflight_result["models"]:
        if model["availability"] != "AVAILABLE":
            rows.append({
                "record_type": "model_availability",
                "comparison_scope": "cloud_reference_only",
                "model": model["model"],
                "model_digest": model["planned_digest"],
                "availability": model["availability"],
                "show_http": model["show_http"],
                "detail": model["detail"],
                "score": None,
            })
    atomic_jsonl(output, rows)
    task_rows = [row for row in rows if row["record_type"] == "task_result"]
    summary = {
        "status": "COMPLETE",
        "comparison_scope": "cloud_reference_only",
        "local_baseline_impact": "none",
        "models_in_inventory": len(preflight_result["models"]),
        "models_tested": len({row["model"] for row in task_rows}),
        "models_unavailable": sum(row["record_type"] == "model_availability" for row in rows),
        "task_records": len(task_rows),
        "scoring_errors": sum(row.get("scoring_status") == "scoring_error" for row in task_rows),
        "missing_raw": sum(not row.get("model") for row in task_rows),
        "output": output.relative_to(ROOT).as_posix(),
        "output_sha256": file_sha256(output),
        "finalized_at": now(),
    }
    atomic_json(output.with_suffix(".summary.json"), summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["preflight", "run", "resume", "status", "finalize"])
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model")
    parser.add_argument("--allow-inference", action="store_true")
    args = parser.parse_args()
    args.run_dir.mkdir(parents=True, exist_ok=True)
    if args.command == "status":
        print(json.dumps(luna_status(args.run_dir), ensure_ascii=False, indent=2))
        return 0
    current_preflight = preflight(args.config, args.plan, args.run_dir)
    if args.command == "preflight":
        print(json.dumps(current_preflight, ensure_ascii=False, indent=2))
        return 0 if current_preflight["status"] == "PASS" else 2
    if args.command == "finalize":
        summary = finalize(args.run_dir, args.output, current_preflight)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    if not args.allow_inference:
        print("RUN_REFUSED: --allow-inference is required for cloud calls")
        return 2
    if current_preflight["status"] != "PASS":
        print("RUN_REFUSED: cloud preflight failed")
        return 2
    bundle = config_bundle(args.config)
    items = build_items(bundle, read(args.plan), current_preflight, args.model)
    if not items:
        print("RUN_REFUSED: no available cloud model has a frozen reference assignment")
        return 2
    state = _run_items(
        bundle,
        items,
        args.run_dir,
        False,
        f"python scripts/cloud_comparison.py resume --allow-inference --run-dir {args.run_dir}",
    )
    incomplete = [item for item in items if state.get("items", {}).get(item["benchmark_version"] + "|" + item["task_manifest_hash"] + "|" + item["model_digest"] + "|" + item["profile"] + "|" + item["task_id"], {}).get("inference_status") not in TERMINAL_INFERENCE]
    if incomplete:
        print(json.dumps({"status": "PARTIAL", "remaining": len(incomplete), "run_dir": str(args.run_dir)}, ensure_ascii=False, indent=2))
        return 2
    summary = finalize(args.run_dir, args.output, current_preflight)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
