"""Offline regrade an RC1 run without modifying immutable inference evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.executor_core import INFRA_FAILURE, EvidenceStore, now
from scripts.rc1_runner import DEFAULT_CONFIG, FormalScorer, config_bundle


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def raw_inventory(run_dir: Path, state: dict[str, Any]) -> dict[str, str]:
    inventory: dict[str, str] = {}
    for entry in (state.get("items") or {}).values():
        relative = entry.get("raw_path")
        path = run_dir / str(relative) if relative else None
        if path and path.is_file():
            inventory[str(relative).replace("\\", "/")] = sha256(path)
    return inventory


def regrade(run_dir: Path, config_path: Path, output: Path, derived_root: Path) -> dict[str, Any]:
    bundle = config_bundle(config_path)
    scorer_version = str(bundle["config"]["scorer_version"])
    scorer = FormalScorer(bundle)
    state = EvidenceStore(run_dir).load_state()
    before = raw_inventory(run_dir, state)
    public_rows: list[dict[str, Any]] = []
    scoring_errors: list[dict[str, str]] = []
    score_count = 0
    infrastructure_count = 0
    repaired_previous_errors = 0

    for logical, entry in (state.get("items") or {}).items():
        relative = entry.get("raw_path")
        raw_path = run_dir / str(relative) if relative else None
        evidence = read(raw_path) if raw_path and raw_path.is_file() else {}
        inference_status = evidence.get("inference_status") or entry.get("inference_status")
        row = {
            "benchmark_version": evidence.get("benchmark_version") or bundle["benchmark"]["benchmark_version"],
            "task_manifest_hash": evidence.get("task_manifest_hash") or bundle["config"]["manifest_hashes"]["task_manifest"],
            "scorer_version": scorer_version,
            "logical_key": logical,
            "model": evidence.get("model"),
            "model_digest": evidence.get("model_digest"),
            "task_id": evidence.get("task_id"),
            "profile": evidence.get("profile"),
            "inference_status": inference_status,
            "done_reason": evidence.get("done_reason"),
            "termination_reason": evidence.get("termination_reason"),
            "runtime_anomaly": evidence.get("runtime_anomaly") is True,
            "terminal_record_seen": evidence.get("terminal_record_seen"),
            "previous_scoring_status": entry.get("scoring_status"),
            "timing": evidence.get("timing", {}),
        }
        if not evidence:
            row["scoring_status"] = "missing_raw"
            scoring_errors.append({"logical_key": logical, "error": "missing_raw"})
        elif inference_status in INFRA_FAILURE:
            infrastructure_count += 1
            row["scoring_status"] = "not_scored_infrastructure"
        else:
            try:
                score = scorer.score(evidence, evidence)
                score_record = {
                    "logical_key": logical,
                    "attempt_id": evidence.get("attempt_id"),
                    "scored_at": now(),
                    "scorer_version": scorer_version,
                    **score,
                }
                relative_score = Path(str(relative)) if relative else Path("unknown") / f"{hashlib.sha256(logical.encode()).hexdigest()}.json"
                score_path = derived_root / "scores" / relative_score.parent.name / relative_score.name
                atomic_json(score_path, score_record)
                row["scoring_status"] = "scored"
                row["score"] = score
                score_count += 1
                if entry.get("scoring_status") == "scoring_error":
                    repaired_previous_errors += 1
            except Exception as exc:
                row["scoring_status"] = "scoring_error"
                row["scoring_error"] = f"{type(exc).__name__}: {exc}"
                scoring_errors.append({"logical_key": logical, "error": row["scoring_error"]})
        public_rows.append(row)

    after = raw_inventory(run_dir, state)
    raw_unchanged = before == after
    if not raw_unchanged:
        raise RuntimeError("immutable raw evidence changed during offline regrade")
    atomic_jsonl(output, public_rows)
    summary = {
        "status": "PASS" if not scoring_errors else "PARTIAL",
        "benchmark_version": bundle["benchmark"]["benchmark_version"],
        "scorer_version": scorer_version,
        "regraded_at": now(),
        "source_run": run_dir.name,
        "records": len(public_rows),
        "scored_records": score_count,
        "infrastructure_records": infrastructure_count,
        "scoring_errors": len(scoring_errors),
        "repaired_previous_scoring_errors": repaired_previous_errors,
        "raw_files": len(before),
        "raw_unchanged": raw_unchanged,
        "output": output.relative_to(ROOT).as_posix() if output.is_relative_to(ROOT) else str(output),
        "output_sha256": sha256(output),
        "errors": scoring_errors,
    }
    atomic_json(derived_root / "summary.json", summary)
    atomic_json(output.with_suffix(".summary.json"), summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--derived-root", type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    bundle = config_bundle(args.config)
    version = str(bundle["config"]["scorer_version"])
    output = args.output or ROOT / "public_results" / f"{run_dir.name}.scorer-{version}.jsonl"
    derived_root = args.derived_root or run_dir / "derived" / f"scorer-{version}"
    summary = regrade(run_dir, args.config, output.resolve(), derived_root.resolve())
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
