"""Validate durable V2 records, raw evidence, and historical-run immutability."""
from __future__ import annotations
import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from benchmark_v2 import canonical_rows, execution_attempt, logical_key

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "benchmark_20260629" / "runs" / "20260730_incremental"

def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_raw_bytes(data: bytes) -> bytes:
    """Hash JSON evidence as logical UTF-8 text, including legacy CRLF files."""
    return data.replace(b"\r\n", b"\n").rstrip(b"\n")

def main(run_dir: str) -> int:
    run = Path(run_dir); failures = []; rows = []
    result_path = run / "results.jsonl"
    for n, line in enumerate(result_path.read_text(encoding="utf-8").splitlines(), 1):
        try: rows.append(json.loads(line))
        except Exception as exc: failures.append(f"jsonl:{n}:{type(exc).__name__}")
    attempt_keys = set()
    for i, row in enumerate(rows, 1):
        attempt_key = logical_key(row) + (execution_attempt(row),)
        if attempt_key in attempt_keys: failures.append(f"duplicate_attempt:{i}:{attempt_key}")
        attempt_keys.add(attempt_key)
        score, maximum = row.get("score"), row.get("max_score")
        if isinstance(score, (int, float)) and isinstance(maximum, (int, float)) and not 0 <= score <= maximum: failures.append(f"score_bounds:{i}")
        raw = row.get("raw_response_path")
        if raw:
            path = run / raw
            if not path.exists(): failures.append(f"raw_missing:{i}:{raw}"); continue
            data = path.read_bytes()
            if path.suffix == ".gz":
                data = gzip.decompress(data)
            if row.get("raw_sha256") and digest_bytes(normalized_raw_bytes(data)) != row["raw_sha256"]: failures.append(f"raw_hash:{i}:{raw}")
    canonical = canonical_rows(rows)
    canonical_path = run / "canonical_results.jsonl"
    if canonical_path.exists():
        stored = []
        for n, line in enumerate(canonical_path.read_text(encoding="utf-8").splitlines(), 1):
            try: stored.append(json.loads(line))
            except Exception as exc: failures.append(f"canonical_jsonl:{n}:{type(exc).__name__}")
        if [logical_key(row) + (execution_attempt(row),) for row in stored] != [logical_key(row) + (execution_attempt(row),) for row in canonical]:
            failures.append("canonical_selection_mismatch")
    old_hash = digest_bytes((OLD / "results.jsonl").read_bytes()) if (OLD / "results.jsonl").exists() else None
    old_git_clean = None
    if OLD.exists():
        old_git_clean = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", str(OLD.relative_to(ROOT))], cwd=ROOT).returncode == 0
        if not old_git_clean: failures.append("historical_run_modified")
    report = {"run_id": run.name, "attempt_records": len(rows), "canonical_records": len(canonical), "unique_logical_keys": len({logical_key(row) for row in rows}), "failures": failures, "old_results_sha256": old_hash, "historical_git_clean": old_git_clean, "status": "passed" if not failures else "failed"}
    (run / "validation_v2.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if not failures else 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[sys.argv.index("--run-dir") + 1]))
