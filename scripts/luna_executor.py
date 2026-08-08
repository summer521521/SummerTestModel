"""Mechanical doctor, status, and mock commands for the future Luna executor."""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

try:
    from executor_core import CircuitBreaker, CircuitConfig, EvidenceStore, Executor, PENDING, SafeCodeHarness, load_json, unresolved
except ModuleNotFoundError:  # Package import during unit tests.
    from scripts.executor_core import CircuitBreaker, CircuitConfig, EvidenceStore, Executor, PENDING, SafeCodeHarness, load_json, unresolved

ROOT = Path(__file__).resolve().parents[1]


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def healthcheck(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/api/version", timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def doctor(config_path: Path) -> tuple[str, list[dict[str, str]]]:
    checks: list[dict[str, str]] = []
    try:
        config = load_json(config_path)
        checks.append({"check": "config_parse", "status": "PASS", "detail": config_path.name})
    except Exception as exc:
        return "NOT_READY", [{"check": "config_parse", "status": "FAIL", "detail": f"{type(exc).__name__}: {exc}"}]
    pending = unresolved(config)
    checks.append({"check": "unresolved_placeholders", "status": "FAIL" if pending else "PASS", "detail": ", ".join(pending) if pending else "none"})
    api = str(config.get("ollama_api") or "http://127.0.0.1:11434")
    checks.append({"check": "ollama_reachable", "status": "PASS" if healthcheck(api) else "FAIL", "detail": api})
    inventory = ROOT / str(config.get("inventory_path") or "")
    checks.append({"check": "inventory_available", "status": "PASS" if inventory.is_file() else "FAIL", "detail": str(config.get("inventory_path"))})
    for key in ("benchmark_manifest", "task_manifest", "scorer_manifest", "model_execution_plan", "generation_profiles", "retry_policy"):
        value = config.get(key)
        path = ROOT / str(value) if value not in (None, PENDING) else None
        checks.append({"check": key, "status": "PASS" if path and path.is_file() else "FAIL", "detail": str(value)})
    hashes = config.get("manifest_hashes") if isinstance(config.get("manifest_hashes"), dict) else {}
    for key, expected in hashes.items():
        value = config.get(key)
        path = ROOT / str(value) if value not in (None, PENDING) else None
        actual = file_sha256(path) if path and path.is_file() else None
        checks.append({"check": f"hash:{key}", "status": "PASS" if actual == expected else "FAIL", "detail": f"expected={expected};actual={actual}"})
    try:
        inventory_data = load_json(inventory)
        inventory_digests = {item.get("exact_name"): item.get("digest") for item in inventory_data.get("models", [])}
        plan_value = config.get("model_execution_plan")
        plan_path = ROOT / str(plan_value) if plan_value not in (None, PENDING) else None
        if plan_path and plan_path.is_file():
            plan = load_json(plan_path)
            entries = plan.get("models") or []
            mismatch = [item.get("model") for item in entries if inventory_digests.get(item.get("model")) != item.get("digest")]
            checks.append({"check": "model_digest_match", "status": "FAIL" if mismatch else "PASS", "detail": ", ".join(str(item) for item in mismatch) if mismatch else "all selected digests match"})
            contamination = [item.get("model") for item in entries if (str(item.get("model", "")).endswith(":cloud") or "-cloud" in str(item.get("model", ""))) != (item.get("local_or_cloud") == "cloud")]
            checks.append({"check": "cloud_local_classification", "status": "FAIL" if contamination else "PASS", "detail": ", ".join(str(item) for item in contamination) if contamination else "consistent"})
    except Exception as exc:
        checks.append({"check": "model_plan_validation", "status": "FAIL", "detail": f"{type(exc).__name__}: {exc}"})
    try:
        task_value = config.get("task_manifest")
        task_path = ROOT / str(task_value) if task_value not in (None, PENDING) else None
        if task_path and task_path.is_file():
            tasks = load_json(task_path).get("tasks") or []
            keys = [(item.get("task_id"), item.get("version")) for item in tasks]
            duplicates = sorted({key for key in keys if keys.count(key) > 1})
            checks.append({"check": "duplicate_task_keys", "status": "FAIL" if duplicates else "PASS", "detail": str(duplicates) if duplicates else "none"})
            bad_assets = []
            for item in tasks:
                for asset in item.get("assets") or []:
                    asset_path = ROOT / str(asset.get("path"))
                    if not asset_path.is_file() or file_sha256(asset_path) != asset.get("sha256"):
                        bad_assets.append(str(asset.get("path")))
            checks.append({"check": "asset_hashes", "status": "FAIL" if bad_assets else "PASS", "detail": ", ".join(bad_assets) if bad_assets else "all declared assets valid"})
    except Exception as exc:
        checks.append({"check": "task_asset_validation", "status": "FAIL", "detail": f"{type(exc).__name__}: {exc}"})
    output = ROOT / str(config.get("output_dir") or "work/pending-run")
    try:
        output.mkdir(parents=True, exist_ok=True)
        probe = output / ".doctor-write-probe"
        probe.write_text("ok", encoding="ascii")
        probe.unlink()
        checks.append({"check": "output_writable", "status": "PASS", "detail": str(config.get("output_dir"))})
    except Exception as exc:
        checks.append({"check": "output_writable", "status": "FAIL", "detail": f"{type(exc).__name__}: {exc}"})
    try:
        result = SafeCodeHarness.run_fixture("def add(a, b): return a + b", "assert add(2, 3) == 5")
        checks.append({"check": "code_sandbox_smoke", "status": "PASS" if result["status"] == "passed" else "FAIL", "detail": result["status"]})
    except Exception as exc:
        checks.append({"check": "code_sandbox_smoke", "status": "FAIL", "detail": f"{type(exc).__name__}: {exc}"})
    try:
        with tempfile.TemporaryDirectory(prefix="summertest-doctor-mock-") as temporary:
            result = mock_run(Path(temporary))
        checks.append({"check": "runner_mock_suite", "status": "PASS" if result.get("duplicate_skipped") and result.get("state_items") == 13 else "FAIL", "detail": json.dumps(result, ensure_ascii=False)})
    except Exception as exc:
        checks.append({"check": "runner_mock_suite", "status": "FAIL", "detail": f"{type(exc).__name__}: {exc}"})
    ready = all(item["status"] == "PASS" for item in checks)
    return "READY" if ready else "NOT_READY", checks


def status(run_dir: Path) -> dict[str, Any]:
    store = EvidenceStore(run_dir)
    state = store.load_state()
    items = state.get("items") or {}
    statuses: dict[str, int] = {}
    scorer_failures = 0
    for item in items.values():
        name = item.get("inference_status") or "unknown"
        statuses[name] = statuses.get(name, 0) + 1
        scorer_failures += int(item.get("scoring_status") == "scoring_error")
    return {
        "run_id": run_dir.name,
        "benchmark_version": state.get("benchmark_version"),
        "total_selected_models": state.get("total_selected_models"),
        "completed_models": state.get("completed_models"),
        "current_model": state.get("current_model"),
        "current_task": state.get("current_task"),
        "successful_tasks": statuses.get("completed", 0),
        "model_failures": sum(value for key, value in statuses.items() if key in {"model_capability_failure", "malformed_response", "truncated", "model_fatal_error"}),
        "infrastructure_failures": sum(value for key, value in statuses.items() if key in {"connection_refused", "http_500", "stream_interrupted", "timeout", "cancelled"}),
        "scorer_failures": scorer_failures,
        "last_checkpoint": state.get("last_checkpoint"),
        "ollama_health": "not_checked_by_status",
        "remaining_task_count": state.get("remaining_task_count"),
        "halted_reason": state.get("halted_reason"),
    }


class MockAdapter:
    def infer(self, item: dict[str, Any]) -> dict[str, Any]:
        scenario = item["scenario"]
        if scenario == "runner_exception":
            raise RuntimeError("mock runner exception")
        if scenario == "cancelled":
            raise KeyboardInterrupt()
        if scenario == "very_long":
            answer = "x" * 200_000
        else:
            answer = {"normal": "ok", "wrong": "wrong", "malformed": "{", "truncated": "partial", "scorer_exception": "score-bomb", "duplicate": "ok", "model_fatal_error": ""}.get(scenario, "")
        status = {
            "connection_refused": "connection_refused", "http_500": "http_500", "stream_interrupted": "stream_interrupted",
            "truncated": "truncated", "model_fatal_error": "model_fatal_error", "malformed": "malformed_response",
        }.get(scenario, "completed")
        return {"status": status, "raw_response": answer, "final_answer": answer, "termination_reason": scenario}


class MockScorer:
    def score(self, evidence: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
        if item["scenario"] == "scorer_exception":
            raise RuntimeError("mock scorer exception")
        return {"status": "scored", "score": int(evidence.get("final_answer") == "ok"), "max_score": 1}


def mock_run(output: Path) -> dict[str, Any]:
    scenarios = ["normal", "wrong", "malformed", "very_long", "truncated", "connection_refused", "http_500", "stream_interrupted", "scorer_exception", "runner_exception", "cancelled", "duplicate", "model_fatal_error"]
    items = [{"benchmark_version": "mock-v1", "model": "mock:model", "model_digest": "mock-digest", "profile": "mock", "task_id": f"MOCK-{index:02d}", "scenario": scenario} for index, scenario in enumerate(scenarios, 1)]
    items.append(dict(items[-2]))
    store = EvidenceStore(output)
    breaker = CircuitBreaker(CircuitConfig(99, 0, 1), healthcheck=lambda: True, sleep=lambda _: None)
    first = Executor(store, MockAdapter(), MockScorer(), breaker).run(items)
    first_count = len(first["items"])
    resumed = Executor(store, MockAdapter(), MockScorer(), breaker).run(items)
    raw_files = list((output / "raw").rglob("*.json"))
    return {"state_items": len(resumed["items"]), "first_state_items": first_count, "raw_files": len(raw_files), "duplicate_skipped": len(resumed["items"]) == len({item["task_id"] for item in items}), "state_path": str(output / "state.json")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    doctor_parser = sub.add_parser("doctor")
    doctor_parser.add_argument("--config", type=Path, default=ROOT / "config/run_config.template.json")
    status_parser = sub.add_parser("status")
    status_parser.add_argument("--run-dir", type=Path, required=True)
    mock_parser = sub.add_parser("mock")
    mock_parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "doctor":
        result, checks = doctor(args.config)
        print(json.dumps({"result": result, "checks": checks}, ensure_ascii=False, indent=2))
        return 0 if result == "READY" else 2
    if args.command == "status":
        print(json.dumps(status(args.run_dir), ensure_ascii=False, indent=2))
        return 0
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        print(json.dumps(mock_run(args.output), ensure_ascii=False, indent=2))
    else:
        with tempfile.TemporaryDirectory(prefix="summertest-mock-") as temporary:
            print(json.dumps(mock_run(Path(temporary)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
