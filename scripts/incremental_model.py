#!/usr/bin/env python3
"""Run one newly installed local model against the frozen RC1 task set.

The caller must explicitly select an existing reference model. Its frozen task
assignment is copied mechanically; this script never invents tasks, scorers, or
capabilities and never reruns previously published models.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.executor_core import EvidenceStore, atomic_json
from scripts.luna_executor import status as luna_status
from scripts.rc1_runner import DEFAULT_CONFIG, RC1ItemBuilder, _run_items, config_bundle
from scripts.regrade_rc1 import regrade


API = "http://127.0.0.1:11434"


def api_json(path: str, payload: dict[str, Any] | None = None, base_url: str = API) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=body,
        headers={"Content-Type": "application/json"},
        method="GET" if body is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"unexpected Ollama response for {path}")
    return value


def model_snapshot(model: str, base_url: str = API) -> dict[str, Any]:
    tags = api_json("/api/tags", base_url=base_url).get("models") or []
    row = next((item for item in tags if item.get("name") == model or item.get("model") == model), None)
    if row is None:
        raise ValueError(f"model is not installed under the exact tag: {model}")
    show = api_json("/api/show", {"model": model}, base_url)
    details = show.get("details") or row.get("details") or {}
    capabilities = show.get("capabilities") or []
    if not isinstance(capabilities, list):
        capabilities = []
    digest = str(row.get("digest") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError(f"invalid or missing digest for {model}")
    return {
        "exact_name": model,
        "tag": model.rsplit(":", 1)[-1],
        "digest": digest,
        "disk_size_bytes": row.get("size"),
        "parameter_size": details.get("parameter_size"),
        "quantization": details.get("quantization_level"),
        "family": details.get("family"),
        "architecture": (show.get("model_info") or {}).get("general.architecture"),
        "context_length": next((value for key, value in (show.get("model_info") or {}).items() if key.endswith(".context_length")), None),
        "capabilities": sorted({str(value) for value in capabilities}),
        "local_or_cloud": "local",
        "currently_installed": True,
        "metadata_source": "/api/tags + /api/show",
        "retention_status": "UNASSESSED",
    }


def _required_capabilities(tracks: list[str]) -> set[str]:
    required: set[str] = set()
    for track in tracks:
        if track == "embedding":
            required.add("embedding")
        elif track in {"vision", "ocr"}:
            required.update({"completion", "vision"})
        elif track == "tools":
            required.update({"completion", "tools"})
        elif track == "reasoning":
            required.update({"completion", "thinking"})
        else:
            required.add("completion")
    return required


def parameter_billions(value: Any) -> float | None:
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*([KMBT])?\s*", str(value or ""), re.IGNORECASE)
    if not match:
        return None
    number = float(match.group(1))
    unit = (match.group(2) or "").upper()
    return number * {"": 1.0, "K": 1e-6, "M": 1e-3, "B": 1.0, "T": 1e3}[unit]


def build_bundle(base: dict[str, Any], snapshot: dict[str, Any], reference_model: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if snapshot["exact_name"] == reference_model:
        raise ValueError("new model and reference model must differ")
    reference = next((row for row in base["plan"]["models"] if row.get("model") == reference_model and row.get("local_or_cloud") == "local"), None)
    if reference is None:
        raise ValueError(f"reference model is not in the frozen local plan: {reference_model}")
    if any(row.get("model") == snapshot["exact_name"] for row in base["plan"]["models"]):
        raise ValueError("model already exists in the frozen baseline; incremental execution would duplicate it")
    max_params = float((base["plan"].get("selection_policy") or {}).get("max_total_params_b", 10.0))
    total_params = parameter_billions(snapshot.get("parameter_size"))
    if total_params is None:
        raise ValueError("new model total parameter count is unavailable; architect/user review is required")
    if total_params > max_params:
        raise ValueError(f"new model exceeds the frozen local scope: {total_params}B > {max_params}B")
    if int(snapshot.get("disk_size_bytes") or 0) < 1024 * 1024:
        raise ValueError("new entry does not have a substantive local model file; cloud/catalog entries are out of scope")
    required = _required_capabilities(list(reference.get("assigned_tracks") or []))
    available = set(snapshot.get("capabilities") or [])
    missing = sorted(required - available)
    if missing:
        raise ValueError(f"new model metadata lacks capabilities required by the selected reference: {missing}")

    bundle = copy.deepcopy(base)
    plan_row = copy.deepcopy(reference)
    plan_row.update(
        {
            "model": snapshot["exact_name"],
            "digest": snapshot["digest"],
            "retention_status": "UNASSESSED",
            "dominated_by": None,
            "dominance_evidence": None,
            "incremental_reference_model": reference_model,
        }
    )
    bundle["plan"]["models"] = [plan_row]
    bundle["inventory"]["models"].append(snapshot)
    bundle["runtime_defaults"]["models"] = [
        {
            "exact_name": snapshot["exact_name"],
            "digest": snapshot["digest"],
            "capabilities": snapshot.get("capabilities") or [],
            "sampling_policy": "native_artifact",
            "retention_status": "UNASSESSED",
        }
    ]
    snapshot_plan = {
        "schema_version": 1,
        "benchmark_version": bundle["benchmark"]["benchmark_version"],
        "scorer_version": bundle["config"]["scorer_version"],
        "task_manifest_hash": bundle["config"]["manifest_hashes"]["task_manifest"],
        "model": snapshot,
        "total_params_b": total_params,
        "reference_model": reference_model,
        "assigned_tracks": plan_row.get("assigned_tracks") or [],
        "task_ids": plan_row.get("task_ids") or [],
        "retention_status": "UNASSESSED",
        "policy": "copy_frozen_assignment_from_explicit_reference",
    }
    return bundle, snapshot_plan


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_") or "model"


def default_run_dir(snapshot: dict[str, Any]) -> Path:
    return ROOT / "private_runs" / f"incremental_{slug(snapshot['exact_name'])}_{snapshot['digest'][:12]}"


def prepare(model: str, reference_model: str, base_url: str = API, run_dir: Path | None = None) -> tuple[dict[str, Any], dict[str, Any], Path]:
    base = config_bundle(DEFAULT_CONFIG)
    snapshot = model_snapshot(model, base_url)
    bundle, plan = build_bundle(base, snapshot, reference_model)
    target = run_dir or default_run_dir(snapshot)
    target.mkdir(parents=True, exist_ok=True)
    plan_path = target / "incremental_execution_plan.json"
    if plan_path.exists():
        existing = json.loads(plan_path.read_text(encoding="utf-8"))
        if existing != plan:
            raise ValueError("existing incremental plan differs; use a new run directory instead of overwriting")
    else:
        atomic_json(plan_path, plan)
    return bundle, plan, target


def public_output(run_dir: Path, scorer_version: str) -> Path:
    return ROOT / "public_results" / f"{run_dir.name}.scorer-{scorer_version}.jsonl"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["inspect", "doctor", "prepare", "run", "resume", "status", "finalize"])
    parser.add_argument("--model")
    parser.add_argument("--reference-model")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--api", default=API)
    parser.add_argument("--allow-inference", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "status":
        if not args.run_dir:
            parser.error("status requires --run-dir")
        print(json.dumps(luna_status(args.run_dir), ensure_ascii=False, indent=2))
        return 0

    if args.command == "finalize":
        if not args.run_dir:
            parser.error("finalize requires --run-dir")
        version = config_bundle(DEFAULT_CONFIG)["config"]["scorer_version"]
        summary = regrade(args.run_dir.resolve(), DEFAULT_CONFIG, public_output(args.run_dir, version), args.run_dir / "derived" / f"scorer-{version}")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary["status"] == "PASS" else 2

    if not args.model:
        parser.error(f"{args.command} requires --model")
    if args.command == "inspect":
        print(json.dumps(model_snapshot(args.model, args.api), ensure_ascii=False, indent=2))
        return 0
    if not args.reference_model:
        parser.error(f"{args.command} requires --reference-model")

    try:
        bundle, plan, run_dir = prepare(args.model, args.reference_model, args.api, args.run_dir)
        items = RC1ItemBuilder(bundle).all_items(selected_model=args.model)
        checks = {
            "ollama_reachable_and_model_installed": True,
            "exact_digest_recorded": bool(plan["model"]["digest"]),
            "explicit_reference_in_frozen_plan": True,
            "capabilities_cover_assignment": True,
            "private_payload_available": bool(items),
            "private_run_git_ignored": str(run_dir.resolve()).lower().startswith(str((ROOT / "private_runs").resolve()).lower()),
        }
    except (ValueError, FileNotFoundError, urllib.error.URLError) as exc:
        print(json.dumps({"status": "NOT_READY", "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False, indent=2))
        return 2

    if args.command in {"doctor", "prepare"}:
        status = "READY" if all(checks.values()) else "NOT_READY"
        print(json.dumps({"status": status, "checks": checks, "run_dir": str(run_dir), "tasks": len(items), "plan": plan}, ensure_ascii=False, indent=2))
        return 0 if status == "READY" else 2

    if not args.allow_inference:
        print(json.dumps({"status": "RUN_REFUSED", "reason": "--allow-inference is required", "run_dir": str(run_dir)}, ensure_ascii=False, indent=2))
        return 2
    resume_command = f'python scripts/incremental_model.py resume --model "{args.model}" --reference-model "{args.reference_model}" --run-dir "{run_dir}" --allow-inference'
    state = _run_items(bundle, items, run_dir, False, resume_command)
    print(json.dumps({"status": "COMPLETED", "tasks": len(items), "state_items": len(state.get("items", {})), "run_dir": str(run_dir), "next": f'python scripts/incremental_model.py finalize --run-dir "{run_dir}"'}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
