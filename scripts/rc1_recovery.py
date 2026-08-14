"""Run the exact isolated RC1 practical recovery queue."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.executor_core import INFRA_FAILURE, CircuitBreaker, CircuitConfig, EvidenceStore, Executor, append_jsonl, atomic_json, logical_key, now
from scripts.ollama_adapter import OllamaAdapter
from scripts.luna_executor import doctor as luna_doctor
from scripts.rc1_runner import FormalScorer, RC1Adapter, RC1ItemBuilder, config_bundle, healthcheck, read

POLICY_PATH = ROOT / "config" / "relaxed_recovery_policy.rc1.json"
EXPECTED_DIGESTS = read(POLICY_PATH)["digests"]


class RecoveryStore(EvidenceStore):
    def __init__(self, run_dir: Path, metadata: dict[str, dict[str, Any]]):
        super().__init__(run_dir, metadata)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); atomic_json(path, value)


def actual_ollama_version(api: str) -> str | None:
    import urllib.request
    try:
        with urllib.request.urlopen(api.rstrip("/") + "/api/version", timeout=5) as response:
            return str(json.loads(response.read().decode()).get("version"))
    except Exception:
        return None


def live_model_digests(api: str) -> dict[str, str]:
    import urllib.request
    with urllib.request.urlopen(api.rstrip("/") + "/api/tags", timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return {str(row.get("name")): str(row.get("digest")) for row in (payload.get("models") or []) if row.get("name") and row.get("digest")}


def validate_recovery_digests(bundle: dict[str, Any], queue: dict[str, list[str]], api: str) -> tuple[dict[str, str], dict[str, Any]]:
    """Require policy, plan, inventory, and live API digests to agree per model."""
    live = live_model_digests(api)
    inventory = {row.get("exact_name"): row.get("digest") for row in bundle["inventory"].get("models", [])}
    plan = {row.get("model"): row.get("digest") for row in bundle["plan"].get("models", [])}
    revisions: dict[str, str] = {}
    details: dict[str, Any] = {"live": live, "models": {}}
    for model in queue:
        values = {"policy": EXPECTED_DIGESTS.get(model), "plan": plan.get(model), "inventory": inventory.get(model), "live": live.get(model)}
        details["models"][model] = values
        if len(set(values.values())) != 1 or None in values.values():
            revisions[model] = "MODEL_REVISION_CHANGED"
    return revisions, details


def make_config(path: Path, output_dir: Path) -> dict[str, Any]:
    config = read(ROOT / "config" / "run_config.template.json")
    try:
        output_value = output_dir.relative_to(ROOT).as_posix()
    except ValueError:
        output_value = str(output_dir)
    config.update({"calibration_approved": True, "purpose": "TARGETED_PRACTICAL_RECOVERY", "approval_basis": "USER_AUTHORIZED_TARGETED_RECOVERY_20260813", "output_dir": output_value})
    write_json(path, config); return config


def load_queue() -> dict[str, list[str]]:
    policy = read(POLICY_PATH); queue = policy["queue"]
    if sum(len(v) for v in queue.values()) != 50 or len({(m, t) for m, tasks in queue.items() for t in tasks}) != 50:
        raise RuntimeError("recovery queue must contain exactly 50 unique items")
    return queue


def prepare_items(bundle: dict[str, Any], queue: dict[str, list[str]], version: str | None, baseline_status: dict[str, str], preblocked: dict[str, str] | None = None) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, str]]:
    builder = RC1ItemBuilder(bundle); models = {row["model"]: row for row in bundle["plan"]["models"]}; items=[]; metadata={}; revisions={}
    for model, task_ids in queue.items():
        row = models.get(model)
        expected = EXPECTED_DIGESTS.get(model)
        if model in (preblocked or {}) or not row or row.get("digest") != expected:
            revisions[model] = (preblocked or {}).get(model, "MODEL_REVISION_CHANGED"); continue
        for task_id in task_ids:
            item = builder.build(row, task_id); original_profile = copy.deepcopy(item["profile_config"]); track = item["track"]
            if track == "reasoning":
                item["profile_config"].update({"think": True, "num_ctx": 32768, "num_predict": 32768, "inactivity_timeout_seconds": 450, "absolute_timeout_seconds": 1800})
                reason = "no_final_reasoning_recovery"
            elif track == "tools":
                item["profile_config"].update({"think": False, "num_predict": 8192, "inactivity_timeout_seconds": 300, "absolute_timeout_seconds": 600, "max_tool_rounds": 5})
                reason = "tool_stability_replay"
            elif track == "long_context_32k":
                item["profile_config"].update({"num_predict": 8192, "inactivity_timeout_seconds": 450, "absolute_timeout_seconds": 1800})
                reason = "long_context_no_final_recovery"
            elif track == "performance":
                item["profile_config"].update({"think": False, "num_predict": 1024, "inactivity_timeout_seconds": 300, "absolute_timeout_seconds": 900})
                reason = "performance_completion_evidence"
            else:
                item["profile_config"].update({"think": False, "num_predict": min(int(original_profile.get("num_predict", 8192)) * 2, 16384), "inactivity_timeout_seconds": 300, "absolute_timeout_seconds": 1800})
                reason = "no_final_practical_recovery"
            item["ollama_version"] = version; item["recovery_policy_id"] = "rc1-relaxed-recovery-v1"; item["recovery_reason"] = reason; item["recovery_used"] = True; item["original_logical_key"] = logical_key(item); item["original_status"] = baseline_status.get(logical_key(item)); items.append(item)
            metadata[logical_key(item)] = {"original_logical_key": logical_key(item), "original_status": baseline_status.get(logical_key(item)), "recovery_reason": reason, "recovery_policy_id": "rc1-relaxed-recovery-v1", "recovery_used": True, "effective_profile": item["profile"], "effective_think": item["profile_config"].get("think"), "effective_options": {key: item["profile_config"].get(key) for key in ("num_ctx", "num_predict", "inactivity_timeout_seconds", "absolute_timeout_seconds", "max_tool_rounds") if item["profile_config"].get(key) is not None}, "current_ollama_version": version}
    return items, metadata, revisions


def run_group(bundle: dict[str, Any], items: list[dict[str, Any]], metadata: dict[str, dict[str, Any]], run_dir: Path, version: str | None, breaker: CircuitBreaker, resume_command: str, mock: bool = False) -> dict[str, Any]:
    store = RecoveryStore(run_dir, metadata)
    state = store.load_state()
    state.update({"benchmark_version": bundle["benchmark"]["benchmark_version"], "recovery_policy_id": "rc1-relaxed-recovery-v1", "current_ollama_version": version, "planned_items": 50})
    store.checkpoint(state)
    # A raw path is already a consumed one-attempt item even if a process died
    # before the last state checkpoint. Executor still provides normal terminal
    # status, scoring isolation, circuit-breaker, and checkpoint semantics.
    pending = [item for item in items if not (state.get("items", {}).get(logical_key(item)) or {}).get("raw_path")]
    base = OllamaAdapter(bundle["config"].get("ollama_api", "http://127.0.0.1:11434"), 1) if not mock else None
    adapter = RC1Adapter(base, mock=mock)
    try:
        scorer = FormalScorer(bundle)
        state = Executor(store, adapter, scorer, breaker, resume_command=resume_command).run(pending)
    finally:
        try:
            adapter.close()
        except Exception as exc:
            append_jsonl(store.events, {"event": "model_unload_error", "at": now(), "error": f"{type(exc).__name__}: {exc}"})
    state["accounted_items"] = len([x for x in (state.get("items") or {}).values() if x.get("raw_path")])
    store.checkpoint(state)
    return state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init"); init.add_argument("--config", type=Path, default=Path("private_runs/rc1_relaxed_recovery_20260813/approved_recovery_config.json")); init.add_argument("--run-dir", type=Path, default=Path("private_runs/rc1_relaxed_recovery_20260813"))
    run = sub.add_parser("run"); run.add_argument("--config", type=Path, required=True); run.add_argument("--run-dir", type=Path, required=True); run.add_argument("--allow-inference", action="store_true"); run.add_argument("--mock", action="store_true")
    args = parser.parse_args(argv); run_dir = args.run_dir.resolve()
    if args.command == "init":
        config = make_config(args.config.resolve(), run_dir); print(json.dumps({"status": "INITIALIZED", "config": str(args.config), "run_dir": str(run_dir), "calibration_approved": config["calibration_approved"]}, ensure_ascii=False, indent=2)); return 0
    if not args.mock and not args.allow_inference: print("RECOVERY_REFUSED: --allow-inference is required"); return 2
    config_path = args.config.resolve()
    if not args.mock:
        doctor_result, doctor_checks = luna_doctor(config_path)
        write_json(args.run_dir.resolve() / "doctor_result.json", {"status": doctor_result, "checks": doctor_checks})
        print(json.dumps({"doctor": doctor_result, "failed_checks": [x for x in doctor_checks if x.get("status") != "PASS"]}, ensure_ascii=False, indent=2), flush=True)
        if doctor_result != "READY":
            print("PRACTICAL_RECOVERY_BLOCKED: doctor is not READY", flush=True)
            return 3
    bundle = config_bundle(config_path); queue = load_queue(); version = actual_ollama_version(bundle["config"].get("ollama_api", "http://127.0.0.1:11434")); baseline_status = {}
    baseline_state = ROOT / "private_runs" / "rc1_baseline_20260809" / "state.json"
    if baseline_state.is_file(): baseline_status = {key: str(value.get("inference_status")) for key, value in (read(baseline_state).get("items") or {}).items()}
    revisions = {}
    digest_details = None
    if args.mock:
        digest_details = {"mode": "mock"}
    else:
        try:
            revisions, digest_details = validate_recovery_digests(bundle, queue, bundle["config"].get("ollama_api", "http://127.0.0.1:11434"))
        except Exception as exc:
            write_json(run_dir / "live_digest_validation.json", {"status": "UNAVAILABLE", "error": f"{type(exc).__name__}: {exc}"})
            print(f"PRACTICAL_RECOVERY_BLOCKED: live digest validation failed: {type(exc).__name__}: {exc}", flush=True)
            return 4
    items, metadata, item_revisions = prepare_items(bundle, queue, version, baseline_status, revisions)
    revisions.update(item_revisions)
    write_json(run_dir / "live_digest_validation.json", digest_details)
    write_json(run_dir / "recovery_plan.json", {"policy_id": "rc1-relaxed-recovery-v1", "planned": 50, "items": [{"logical_key": logical_key(x), "model": x["model"], "task_id": x["task_id"]} for x in items], "revisions": revisions, "current_ollama_version": version})
    policy = read(ROOT / "config" / "retry_policy.rc1.json")["circuit_breaker"]
    breaker = CircuitBreaker(CircuitConfig(int(policy["consecutive_connection_refused_threshold"]), float(policy["healthcheck_wait_seconds"]), float(policy["max_recovery_seconds"])), lambda: True if args.mock else healthcheck(bundle["config"].get("ollama_api", "http://127.0.0.1:11434")))
    try:
        run_display = run_dir.relative_to(ROOT).as_posix()
    except ValueError:
        run_display = str(run_dir)
    resume_command = f"python scripts/rc1_recovery.py run --config {config_path.relative_to(ROOT).as_posix()} --run-dir {run_display} --allow-inference"
    grouped = []
    for model in queue:
        group = [item for item in items if item["model"] == model]
        if group: grouped.append(run_group(bundle, group, metadata, run_dir, version, breaker, resume_command, args.mock))
    final = read(run_dir / "state.json") if (run_dir / "state.json").is_file() else {"items": {}}
    final["model_revision_changed"] = revisions; final["planned_items"] = 50; final["accounted_items"] = len([x for x in (final.get("items") or {}).values() if x.get("raw_path")]); write_json(run_dir / "recovery_summary.json", final)
    print(json.dumps({"status": "COMPLETE" if final["accounted_items"] == len(items) else "PARTIAL", "planned": 50, "eligible": len(items), "accounted": final["accounted_items"], "model_revision_changed": revisions, "ollama_version": version}, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
