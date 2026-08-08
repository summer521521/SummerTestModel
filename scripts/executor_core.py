"""Specification-free execution primitives for a future frozen benchmark."""
from __future__ import annotations

import ast
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

PENDING = "__PENDING_WEB_GPT_DECISION__"
TERMINAL_INFERENCE = {
    "completed",
    "model_capability_failure",
    "malformed_response",
    "truncated",
    "model_fatal_error",
}
INFRA_FAILURE = {"connection_refused", "http_500", "stream_interrupted", "timeout", "cancelled"}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="milliseconds")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    with temporary.open("wb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def atomic_json(path: Path, value: Any) -> None:
    atomic_bytes(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    with path.open("ab") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def unresolved(value: Any, prefix: str = "") -> list[str]:
    paths: list[str] = []
    if value is None or value == PENDING:
        paths.append(prefix or "$")
    elif isinstance(value, dict):
        for key, child in value.items():
            paths.extend(unresolved(child, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(unresolved(child, f"{prefix}[{index}]"))
    return paths


def logical_key(item: dict[str, Any]) -> str:
    fields = ("benchmark_version", "model_digest", "profile", "task_id")
    missing = [field for field in fields if not item.get(field)]
    if missing:
        raise ValueError(f"missing logical key fields: {missing}")
    return "|".join(str(item[field]) for field in fields)


class Adapter(Protocol):
    def infer(self, item: dict[str, Any]) -> dict[str, Any]: ...


class Scorer(Protocol):
    def score(self, evidence: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]: ...


@dataclass
class CircuitConfig:
    consecutive_failures: int
    recovery_wait_seconds: float
    max_recovery_seconds: float


class CircuitBreaker:
    def __init__(self, config: CircuitConfig, healthcheck: Callable[[], bool], sleep: Callable[[float], None] = time.sleep):
        self.config = config
        self.healthcheck = healthcheck
        self.sleep = sleep
        self.failures = 0
        self.opened_at: float | None = None

    def success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def failure(self, status: str) -> None:
        if status != "connection_refused":
            return
        self.failures += 1
        if self.failures >= self.config.consecutive_failures and self.opened_at is None:
            self.opened_at = time.monotonic()

    def permit(self) -> bool:
        if self.opened_at is None:
            return True
        if self.healthcheck():
            self.success()
            return True
        if time.monotonic() - self.opened_at >= self.config.max_recovery_seconds:
            return False
        self.sleep(self.config.recovery_wait_seconds)
        return self.healthcheck()


class EvidenceStore:
    def __init__(self, run_dir: Path):
        self.run_dir = run_dir
        self.events = run_dir / "events.jsonl"
        self.state_path = run_dir / "state.json"
        self.raw_dir = run_dir / "raw"
        run_dir.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"version": 1, "items": {}, "last_checkpoint": None}
        try:
            return load_json(self.state_path)
        except (json.JSONDecodeError, ValueError):
            quarantine = self.state_path.with_suffix(f".corrupt.{int(time.time())}.json")
            os.replace(self.state_path, quarantine)
            append_jsonl(self.events, {"event": "state_quarantined", "at": now(), "path": quarantine.name})
            return self.rebuild_state()

    def rebuild_state(self) -> dict[str, Any]:
        state = {"version": 1, "items": {}, "last_checkpoint": None}
        if self.events.exists():
            with self.events.open(encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    key = event.get("logical_key")
                    if key and event.get("event") in {"inference_saved", "scoring_saved", "item_failed"}:
                        state["items"][key] = {
                            "inference_status": event.get("inference_status"),
                            "scoring_status": event.get("scoring_status"),
                            "raw_path": event.get("raw_path"),
                        }
        self.checkpoint(state)
        return state

    def checkpoint(self, state: dict[str, Any]) -> None:
        state["last_checkpoint"] = now()
        atomic_json(self.state_path, state)

    def begin(self, item: dict[str, Any], attempt_id: str) -> None:
        append_jsonl(self.events, {
            "event": "attempt_started", "at": now(), "logical_key": logical_key(item), "attempt_id": attempt_id,
            "model": item["model"], "model_digest": item["model_digest"], "benchmark_version": item["benchmark_version"],
            "task_id": item["task_id"], "profile": item["profile"],
        })

    def save_inference(self, item: dict[str, Any], attempt_id: str, response: dict[str, Any]) -> dict[str, Any]:
        key = logical_key(item)
        safe = hashlib.sha256(key.encode()).hexdigest()[:20]
        path = self.raw_dir / safe / f"{attempt_id}.json"
        evidence = {
            "schema_version": 1,
            "logical_key": key,
            "attempt_id": attempt_id,
            "started_at": response.get("started_at"),
            "finished_at": response.get("finished_at") or now(),
            "model": item["model"],
            "model_digest": item["model_digest"],
            "benchmark_version": item["benchmark_version"],
            "task_id": item["task_id"],
            "profile": item["profile"],
            "inference_status": response.get("status", "runner_exception"),
            "raw_response": response.get("raw_response"),
            "thinking": response.get("thinking"),
            "final_answer": response.get("final_answer"),
            "ollama_metadata": response.get("ollama_metadata") or {},
            "timing": response.get("timing") or {},
            "termination_reason": response.get("termination_reason"),
            "error": response.get("error"),
        }
        payload = (json.dumps(evidence, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        evidence["evidence_sha256"] = sha256_bytes(payload)
        atomic_json(path, evidence)
        relative = path.relative_to(self.run_dir).as_posix()
        append_jsonl(self.events, {
            "event": "inference_saved", "at": now(), "logical_key": key, "attempt_id": attempt_id,
            "inference_status": evidence["inference_status"], "raw_path": relative,
            "raw_sha256": evidence["evidence_sha256"],
        })
        return {**evidence, "raw_path": relative}

    def save_score(self, item: dict[str, Any], attempt_id: str, score: dict[str, Any]) -> str:
        key = logical_key(item)
        safe = hashlib.sha256(key.encode()).hexdigest()[:20]
        path = self.run_dir / "scores" / safe / f"{attempt_id}.json"
        atomic_json(path, {"logical_key": key, "attempt_id": attempt_id, "scored_at": now(), **score})
        relative = path.relative_to(self.run_dir).as_posix()
        append_jsonl(self.events, {
            "event": "scoring_saved", "at": now(), "logical_key": key, "attempt_id": attempt_id,
            "inference_status": item.get("inference_status"), "scoring_status": score.get("status", "scored"),
            "score_path": relative,
        })
        return relative


class Executor:
    def __init__(self, store: EvidenceStore, adapter: Adapter, scorer: Scorer, breaker: CircuitBreaker):
        self.store = store
        self.adapter = adapter
        self.scorer = scorer
        self.breaker = breaker

    def run(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        state = self.store.load_state()
        for item in items:
            key = logical_key(item)
            prior = state["items"].get(key) or {}
            if prior.get("inference_status") in TERMINAL_INFERENCE and prior.get("raw_path"):
                continue
            if not self.breaker.permit():
                state["halted_reason"] = "circuit_breaker_recovery_exhausted"
                self.store.checkpoint(state)
                break
            attempt_id = f"attempt-{int(time.time() * 1000)}"
            self.store.begin(item, attempt_id)
            try:
                response = self.adapter.infer(item)
            except KeyboardInterrupt:
                response = {"status": "cancelled", "error": "KeyboardInterrupt", "finished_at": now()}
            except Exception as exc:
                response = {"status": "runner_exception", "error": f"{type(exc).__name__}: {exc}", "finished_at": now()}
            evidence = self.store.save_inference(item, attempt_id, response)
            inference_status = evidence["inference_status"]
            self.breaker.failure(inference_status)
            if inference_status not in INFRA_FAILURE and inference_status != "runner_exception":
                self.breaker.success()
            score_status = "not_scored"
            try:
                score = self.scorer.score(evidence, item)
                self.store.save_score({**item, "inference_status": inference_status}, attempt_id, score)
                score_status = score.get("status", "scored")
            except Exception as exc:
                score_status = "scoring_error"
                append_jsonl(self.store.events, {
                    "event": "scoring_error", "at": now(), "logical_key": key,
                    "attempt_id": attempt_id, "error": f"{type(exc).__name__}: {exc}",
                })
            state["items"][key] = {
                "inference_status": inference_status,
                "scoring_status": score_status,
                "raw_path": evidence["raw_path"],
            }
            self.store.checkpoint(state)
        return state


class SafeCodeHarness:
    BANNED_NAMES = {"open", "exec", "eval", "compile", "__import__", "input", "breakpoint"}
    BANNED_MODULES = {"os", "sys", "subprocess", "socket", "pathlib", "shutil", "requests", "urllib"}

    @classmethod
    def validate(cls, code: str) -> None:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                raise ValueError("imports are disabled in the preparation harness")
            if isinstance(node, ast.Name) and node.id in cls.BANNED_NAMES:
                raise ValueError(f"blocked name: {node.id}")
            if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
                raise ValueError("blocked private/dunder attribute")

    @classmethod
    def run_fixture(cls, code: str, fixture: str, timeout_seconds: float = 2.0) -> dict[str, Any]:
        cls.validate(code)
        with tempfile.TemporaryDirectory(prefix="summertest-code-harness-") as temporary:
            script = Path(temporary) / "fixture.py"
            wrapper = (
                "SAFE = {'abs':abs,'all':all,'any':any,'bool':bool,'dict':dict,'enumerate':enumerate,"
                "'float':float,'int':int,'len':len,'list':list,'max':max,'min':min,'range':range,"
                "'reversed':reversed,'round':round,'set':set,'sorted':sorted,'str':str,'sum':sum,'tuple':tuple,'zip':zip}\n"
                "NS = {'__builtins__': SAFE}\n"
                f"MODEL_CODE = {code!r}\n"
                f"FIXTURE = {fixture!r}\n"
                "exec(compile(MODEL_CODE, '<model>', 'exec'), NS, NS)\n"
                "exec(compile(FIXTURE, '<fixture>', 'exec'), NS, NS)\n"
            )
            script.write_text(wrapper, encoding="utf-8")
            try:
                result = subprocess.run(
                    [sys.executable, "-I", "-S", str(script)], cwd=temporary, capture_output=True, text=True,
                    timeout=timeout_seconds, env={"PYTHONIOENCODING": "utf-8", "PYTHONNOUSERSITE": "1"},
                )
                return {"status": "passed" if result.returncode == 0 else "failed", "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
            except subprocess.TimeoutExpired:
                return {"status": "timeout", "returncode": None, "stdout": "", "stderr": ""}
