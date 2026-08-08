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

def pending_markers(value: Any, prefix: str = "") -> list[str]:
    paths = []
    if value == PENDING:
        paths.append(prefix or "$")
    elif isinstance(value, dict):
        for key, child in value.items(): paths.extend(pending_markers(child, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value): paths.extend(pending_markers(child, f"{prefix}[{index}]"))
    return paths


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def schema_check(document: Path, schema: Path) -> tuple[bool,str]:
    try:
        import jsonschema
        jsonschema.validate(load_json(document), load_json(schema))
        return True, "valid"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


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
    checks.append({"check": "benchmark_version", "status": "PASS" if config.get("benchmark_version") in (None, "1.0-rc1") else "FAIL", "detail": str(config.get("benchmark_version"))})
    calibration_required = config.get("benchmark_version") == "1.0-rc1" or "calibration_approved" in config
    checks.append({"check": "calibration_approved", "status": "PASS" if not calibration_required or config.get("calibration_approved") is True else "FAIL", "detail": "must remain false until Web GPT approval" if calibration_required and config.get("calibration_approved") is not True else "not required for legacy mock" if not calibration_required else "approved"})
    checks.append({"check": "ollama_reachable", "status": "PASS" if healthcheck(api) else "FAIL", "detail": api})
    inventory = ROOT / str(config.get("inventory_path") or "")
    checks.append({"check": "inventory_available", "status": "PASS" if inventory.is_file() else "FAIL", "detail": str(config.get("inventory_path"))})
    for key in ("benchmark_manifest", "task_manifest", "scorer_manifest", "model_execution_plan", "generation_profiles", "retry_policy"):
        value = config.get(key)
        path = ROOT / str(value) if value not in (None, PENDING) else None
        checks.append({"check": key, "status": "PASS" if path and path.is_file() else "FAIL", "detail": str(value)})
        if path and path.is_file():
            nested_pending = pending_markers(load_json(path))
            checks.append({"check": f"placeholders:{key}", "status": "FAIL" if nested_pending else "PASS", "detail": ", ".join(nested_pending) if nested_pending else "none"})
    if config.get("benchmark_version") == "1.0-rc1":
        try:
            manifest = load_json(ROOT / str(config["benchmark_manifest"]))
            checks.append({"check":"rc1_track_ids","status":"PASS" if manifest.get("track_ids") == ["core","reasoning","code","translation","tools","vision","ocr","long_context","embedding","safety","medical","performance"] else "FAIL","detail":"frozen track list"})
            plan = load_json(ROOT / str(config["model_execution_plan"]))
            bad_retention = [m.get("model") for m in plan.get("models",[]) if m.get("retention_status") != "UNASSESSED"]
            checks.append({"check":"retention_unassessed","status":"PASS" if not bad_retention else "FAIL","detail":"all candidates UNASSESSED" if not bad_retention else ",".join(bad_retention)})
            retry = load_json(ROOT / str(config["retry_policy"]))
            circuit = retry.get("circuit_breaker") or {}
            retry_ok = retry.get("max_transport_retries") == 1 and circuit == {"consecutive_connection_refused_threshold":3,"healthcheck_wait_seconds":30,"max_recovery_seconds":900,"auto_restart":False}
            checks.append({"check":"rc1_retry_and_circuit","status":"PASS" if retry_ok else "FAIL","detail":"retry=1; circuit=3/30/900; no auto restart"})
            private_path = ROOT / str(config.get("private_package_manifest") or "")
            private_expected = manifest.get("private_package_manifest_sha256")
            private_actual = file_sha256(private_path) if private_path.is_file() else None
            checks.append({"check":"private_package_hash","status":"PASS" if private_expected and private_actual == private_expected else "FAIL","detail":f"expected={private_expected};actual={private_actual}"})
            for name, schema_name in (("benchmark_manifest","benchmark_manifest.schema.json"),("task_manifest","task_manifest.schema.json"),("scorer_manifest","scorer_manifest.schema.json"),("model_execution_plan","model_execution_plan.schema.json")):
                value=config.get(name); path=ROOT/str(value); schema=ROOT/"config"/schema_name
                ok, detail=schema_check(path,schema); checks.append({"check":f"schema:{name}","status":"PASS" if ok else "FAIL","detail":detail})
            task_data=load_json(ROOT/str(config["task_manifest"])); private_root=ROOT/"private_benchmark"/"1.0-rc1"; hash_errors=[]
            for task in task_data.get("tasks",[]):
                task_file=private_root/"tasks"/(task["task_id"]+".json"); gt_file=private_root/"ground_truth"/(task["task_id"]+".json"); spec_file=private_root/"scoring_specs"/(task["task_id"]+".json")
                if not task_file.is_file() or not spec_file.is_file() or (task.get("ground_truth_sha256") is not None and not gt_file.is_file()): hash_errors.append(task["task_id"]); continue
                private_task=load_json(task_file); actual_prompt=hashlib.sha256(str(private_task.get("prompt","")).encode("utf-8")).hexdigest()
                if actual_prompt != task.get("prompt_sha256") or file_sha256(spec_file)!=task.get("scoring_spec_sha256"): hash_errors.append(task["task_id"])
                if task.get("ground_truth_sha256") is not None and file_sha256(gt_file)!=task.get("ground_truth_sha256"): hash_errors.append(task["task_id"])
                if task.get("scored") and task_file.read_bytes()==gt_file.read_bytes(): hash_errors.append(task["task_id"])
            checks.append({"check":"private_task_hashes","status":"PASS" if not hash_errors else "FAIL","detail":"all task/GT/spec hashes match" if not hash_errors else ",".join(hash_errors)})
            code_errors=[p.name for p in (private_root/"hidden_tests").glob("CODE_*.json") if len((load_json(p).get("cases") or []))!=10]
            checks.append({"check":"code_hidden_tests","status":"PASS" if len(list((private_root/"hidden_tests").glob("CODE_*.json")))==8 and not code_errors else "FAIL","detail":"8 tasks x 10 cases" if not code_errors else ",".join(code_errors)})
            contexts=json.loads((private_root/"long_context/metadata.json").read_text(encoding="utf-8")); checks.append({"check":"long_context_payloads","status":"PASS" if isinstance(contexts, list) and len(contexts)==4 and all(x.get("target_occurrences")==1 for x in contexts) else "FAIL","detail":"four unique targets"})
            embedding_docs=json.loads((private_root/"embedding/corpus.json").read_text(encoding="utf-8")); embedding_queries=json.loads((private_root/"embedding/queries.json").read_text(encoding="utf-8")); checks.append({"check":"embedding_counts","status":"PASS" if isinstance(embedding_docs,list) and isinstance(embedding_queries,list) and len(embedding_docs)==24 and len(embedding_queries)==12 else "FAIL","detail":f"docs={len(embedding_docs)};queries={len(embedding_queries)}"})
            safety=json.loads((private_root/"safety/tasks.json").read_text(encoding="utf-8")); checks.append({"check":"safety_counts","status":"PASS" if isinstance(safety,list) and sum(x.get("label")=="safe" for x in safety)==10 and sum(x.get("label")=="unsafe" for x in safety)==10 else "FAIL","detail":"10 safe + 10 unsafe"})
            scorer_manifest=load_json(ROOT/str(config["scorer_manifest"])); scorer_hash=hashlib.sha256((ROOT/"scripts/scorers.py").read_bytes()).hexdigest(); bad_scorers=[x.get("scorer_id") for x in scorer_manifest.get("scorers",[]) if x.get("sha256")!=scorer_hash]
            checks.append({"check":"scorer_implementation_hashes","status":"PASS" if not bad_scorers else "FAIL","detail":"all scorer entrypoints match scripts/scorers.py" if not bad_scorers else ",".join(bad_scorers)})
        except Exception as exc:
            checks.append({"check":"rc1_policy_files","status":"FAIL","detail":f"{type(exc).__name__}: {exc}"})
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
                    if not asset_path.is_file():
                        asset_path = ROOT / "private_benchmark" / "1.0-rc1" / str(asset.get("path"))
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
    items = [{"benchmark_version": "mock-v1", "task_manifest_hash": "mock-task-hash", "model": "mock:model", "model_digest": "mock-digest", "profile": "mock", "task_id": f"MOCK-{index:02d}", "scenario": scenario} for index, scenario in enumerate(scenarios, 1)]
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
