#!/usr/bin/env python3
"""Validate the sanitized RC1 practical snapshot and optional private evidence."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public_results"
SNAPSHOT = PUBLIC / "rc1_practical_20260813.jsonl"
SUMMARY = PUBLIC / "rc1_practical_20260813.summary.json"
RECOVERY = PUBLIC / "rc1_practical_recovery_20260813.csv"
TRACKS = PUBLIC / "rc1_practical_track_scores.csv"
STRICT = PUBLIC / "rc1_baseline_20260809.scorer-1.0-rc1.1.jsonl"

FORBIDDEN_FIELDS = {
    "final_answer", "thinking", "raw_response", "streamed_chunks", "request_payload",
    "prompt", "messages", "ground_truth", "hidden_tests", "raw_path", "score_path",
}
INFRA = {"connection_refused", "network_error", "server_error", "unavailable", "auth_required", "http_500", "http_502", "http_503", "http_504"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def validate(private_run: Path | None = None) -> dict[str, Any]:
    failures: list[str] = []
    rows = read_jsonl(SNAPSHOT)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    logical_keys = [row.get("logical_key") for row in rows]
    check(len(rows) == 1938, f"practical row count={len(rows)}", failures)
    check(len(set(logical_keys)) == len(rows), "duplicate practical logical_key", failures)
    check(not any(FORBIDDEN_FIELDS.intersection(row) for row in rows), "forbidden private field in practical JSONL", failures)
    check(all(row.get("result_set") == "practical-regrade-with-targeted-recovery" for row in rows), "result_set mismatch", failures)
    check(all(not isinstance(row.get("practical_score_0_to_100"), (int, float)) or 0 <= float(row["practical_score_0_to_100"]) <= 100 for row in rows), "practical score outside 0..100", failures)
    check(all(row.get("practical_score_0_to_100") is None for row in rows if row.get("inference_status") in INFRA), "infrastructure failure received capability score", failures)
    check(summary.get("total") == len(rows), "summary total mismatch", failures)
    check(summary.get("practical_result_sha256") == sha256(SNAPSHOT), "practical snapshot SHA mismatch", failures)
    check(summary.get("strict_baseline_sha256") == sha256(STRICT), "strict baseline SHA mismatch", failures)
    check(summary.get("strict_baseline_replaced") is False, "strict replacement flag is not false", failures)
    check(summary.get("contains_raw_answers") is False, "raw-answer privacy flag is not false", failures)

    with RECOVERY.open(encoding="utf-8", newline="") as handle:
        recovery_rows = list(csv.DictReader(handle))
    selected = sum(row.get("recovery_selected") == "True" for row in recovery_rows)
    check(len(recovery_rows) == 50, f"recovery comparison count={len(recovery_rows)}", failures)
    check(summary.get("recovery_accounted") == len(recovery_rows), "recovery accounted mismatch", failures)
    check(summary.get("recovery_selected") == selected, "recovery selected mismatch", failures)
    check(sum(bool(row.get("recovery_selected")) for row in rows) == selected, "selected flags do not match merged JSONL", failures)

    with TRACKS.open(encoding="utf-8", newline="") as handle:
        track_rows = list(csv.DictReader(handle))
    check(len({row["model"] for row in track_rows}) == 39, "model-track table does not cover 39 models", failures)
    check(all(0 <= float(row["mean_score_0_to_1"]) <= 1 for row in track_rows if row.get("mean_score_0_to_1")), "track mean outside 0..1", failures)
    check(all(0 <= float(row["completion_rate"]) <= 1 for row in track_rows), "completion rate outside 0..1", failures)
    check((ROOT / "site" / "data" / "rc1_model_assessments.json").read_bytes() == (PUBLIC / "rc1_model_assessments.json").read_bytes(), "site/public assessment data differ", failures)

    private_raw_checked = 0
    if private_run is not None:
        hash_manifest = json.loads((private_run / "baseline_raw_hashes.json").read_text(encoding="utf-8"))
        hashes = hash_manifest.get("hashes") or {}
        baseline_run = ROOT / "private_runs" / "rc1_baseline_20260809"
        for relative, expected in hashes.items():
            path = baseline_run / relative
            if not path.is_file() or sha256(path) != expected:
                failures.append(f"strict raw hash mismatch: {relative}")
            private_raw_checked += 1
        check(private_raw_checked == 1938, f"strict raw hash count={private_raw_checked}", failures)
        raw_count = len(list((private_run / "raw").glob("*/*.json")))
        score_count = len(list((private_run / "scores").glob("*/*.json")))
        check(raw_count == 50, f"recovery raw count={raw_count}", failures)
        check(score_count == 50, f"recovery score count={score_count}", failures)

    return {
        "status": "PASS" if not failures else "FAIL",
        "records": len(rows),
        "models": len({row.get("model") for row in rows}),
        "recovery_records": len(recovery_rows),
        "recovery_selected": selected,
        "strict_raw_hashes_checked": private_raw_checked,
        "strict_sha256": sha256(STRICT),
        "practical_sha256": sha256(SNAPSHOT),
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-run", type=Path)
    args = parser.parse_args()
    result = validate(args.private_run.resolve() if args.private_run else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
