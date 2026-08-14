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
    "truncated_before_final", "timeout_before_final", "absolute_timeout", "inactivity_timeout", "scoring_error",
    "stream_interrupted_after_output",
}
INFRA_FAILURE = {
    "connection_refused", "http_500", "http_502", "http_503", "http_504",
    "stream_interrupted", "stream_interrupted_before_output", "timeout", "cancelled", "runner_exception",
}


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
    fields = ("benchmark_version", "task_manifest_hash", "model_digest", "profile", "task_id")
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
        started = self.opened_at
        while time.monotonic() - started < self.config.max_recovery_seconds:
            self.sleep(self.config.recovery_wait_seconds)
            if self.healthcheck():
                self.success()
                return True
        return False


class EvidenceStore:
    def __init__(self, run_dir: Path, extra_fields: dict[str, dict[str, Any]] | None = None):
        self.run_dir = run_dir
        self.events = run_dir / "events.jsonl"
        self.state_path = run_dir / "state.json"
        self.raw_dir = run_dir / "raw"
        self.extra_fields = extra_fields or {}
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
            "task_id": item["task_id"], "profile": item["profile"], "task_manifest_hash": item["task_manifest_hash"],
            "exact_model_tag": item.get("exact_model_tag") or item.get("model"), "ollama_version": item.get("ollama_version"),
            "machine_profile_hash": item.get("machine_profile_hash"), "scorer_version": item.get("scorer_version"),
        })

    def save_inference(self, item: dict[str, Any], attempt_id: str, response: dict[str, Any]) -> dict[str, Any]:
        key = logical_key(item)
        safe = hashlib.sha256(key.encode()).hexdigest()[:20]
        path = self.raw_dir / safe / f"{attempt_id}.json"
        evidence = {
            "schema_version": 1,
            "logical_key": key,
            "attempt_id": attempt_id,
            "started_at": response.get("started_at") or response.get("request_started_at") or (response.get("timing") or {}).get("request_started_at"),
            "finished_at": response.get("finished_at") or now(),
            "model": item["model"],
            "model_digest": item["model_digest"],
            "benchmark_version": item["benchmark_version"],
            "task_manifest_hash": item["task_manifest_hash"],
            "task_id": item["task_id"],
            "profile": item["profile"],
            "exact_model_tag": item.get("exact_model_tag") or item.get("model"),
            "ollama_version": item.get("ollama_version"), "machine_profile_hash": item.get("machine_profile_hash"), "scorer_version": item.get("scorer_version"),
            "inference_status": response.get("status", "runner_exception"),
            "meaningful": bool(response.get("meaningful", False)),
            "retryable": response.get("retryable"),
            "raw_response": response.get("raw_response"),
            "thinking": response.get("thinking"),
            "final_answer": response.get("final_answer"),
            "ollama_metadata": response.get("ollama_metadata") or {},
            "timing": response.get("timing") or {},
            "termination_reason": response.get("termination_reason"),
            "error": response.get("error"),
            "think_reason": response.get("think_reason"),
            "request_payload": response.get("request_payload"), "streamed_chunks": response.get("streamed_chunks"),
            "tool_calls": response.get("tool_calls"), "tool_trace": response.get("tool_trace"),
            "images_sent": response.get("images_sent") or item.get("images"),
            "embedding": response.get("embedding"), "query_embedding": response.get("query_embedding"),
            "embedding_corpus": response.get("embedding_corpus"), "corpus_embeddings": response.get("corpus_embeddings"),
            "seed_applied": response.get("seed_applied"),
            "sampling_policy": response.get("sampling_policy", item.get("sampling_policy", "native_artifact")),
            "runtime_defaults_snapshot_hash": item.get("runtime_defaults_snapshot_hash"),
            "model_modelfile_sha256": item.get("model_modelfile_sha256"),
            "reasoning_mode": response.get("reasoning_mode", item.get("reasoning_mode")),
            "terminal_record_seen": bool(response.get("terminal_record_seen", False)),
            "done_reason": response.get("done_reason", response.get("termination_reason")),
            "runtime_anomaly": bool(response.get("runtime_anomaly", False)),
            "completion_terminal_record": bool(response.get("completion_terminal_record", False)),
            "practical_within_soft_limit": response.get("practical_within_soft_limit") if response.get("practical_within_soft_limit") is not None else (response.get("timing") or {}).get("practical_within_soft_limit"),
            "preload": response.get("preload"),
            "request_started_at": response.get("request_started_at") or (response.get("timing") or {}).get("request_started_at"),
            "first_chunk_at": (response.get("timing") or {}).get("first_chunk_at"),
            "first_generated_at": (response.get("timing") or {}).get("first_generated_at"),
            "first_thinking_at": (response.get("timing") or {}).get("first_thinking_at"),
            "first_final_at": (response.get("timing") or {}).get("first_final_at"),
            "terminal_record_at": (response.get("timing") or {}).get("terminal_record_at"),
            "request_finished_at": response.get("request_finished_at") or (response.get("timing") or {}).get("request_finished_at"),
        }
        # Optional derived-run metadata is inserted before the single atomic
        # write so event.raw_sha256 always describes the final evidence file.
        allowed_extra = {
            "original_logical_key", "original_status", "recovery_reason",
            "recovery_policy_id", "recovery_used", "effective_profile",
            "effective_think", "effective_options", "current_ollama_version",
        }
        for field in allowed_extra:
            if field in self.extra_fields.get(key, {}):
                evidence[field] = self.extra_fields[key][field]
        payload = (json.dumps(evidence, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        evidence["evidence_payload_sha256"] = sha256_bytes(payload)
        atomic_json(path, evidence)
        raw_file_sha256 = sha256_bytes(path.read_bytes())
        relative = path.relative_to(self.run_dir).as_posix()
        append_jsonl(self.events, {
            "event": "inference_saved", "at": now(), "logical_key": key, "attempt_id": attempt_id,
            "inference_status": evidence["inference_status"], "raw_path": relative,
            "raw_sha256": raw_file_sha256,
            "terminal_record_seen": evidence["terminal_record_seen"],
            "runtime_anomaly": evidence["runtime_anomaly"],
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
    def __init__(self, store: EvidenceStore, adapter: Adapter, scorer: Scorer, breaker: CircuitBreaker, resume_command: str | None = None):
        self.store = store
        self.adapter = adapter
        self.scorer = scorer
        self.breaker = breaker
        self.resume_command = resume_command

    def run(self, items: list[dict[str, Any]]) -> dict[str, Any]:
        state = self.store.load_state()
        for item in items:
            key = logical_key(item)
            prior = state["items"].get(key) or {}
            if prior.get("inference_status") in TERMINAL_INFERENCE and prior.get("raw_path"):
                continue
            if not self.breaker.permit():
                state["halted_reason"] = "circuit_breaker_recovery_exhausted"
                state["resume_command"] = self.resume_command
                self.store.checkpoint(state)
                append_jsonl(self.store.events, {"event":"circuit_breaker_recovery_exhausted","at":now(),"resume_command":self.resume_command})
                if self.resume_command:
                    print(f"RESUME_COMMAND: {self.resume_command}", flush=True)
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
            if inference_status not in INFRA_FAILURE:
                self.breaker.success()
            score_status = "not_scored"
            if inference_status not in INFRA_FAILURE:
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
            else:
                score_status = "infrastructure_incomplete"
            state["items"][key] = {
                "inference_status": inference_status,
                "scoring_status": score_status,
                "raw_path": evidence["raw_path"],
                "terminal_record_seen": evidence.get("terminal_record_seen"),
                "runtime_anomaly": evidence.get("runtime_anomaly"),
            }
            self.store.checkpoint(state)
        return state


class SafeCodeHarness:
    BANNED_NAMES = {"open", "exec", "eval", "compile", "__import__", "input", "breakpoint", "globals", "locals", "vars", "getattr", "setattr", "delattr"}
    BANNED_MODULES = {"os", "sys", "subprocess", "socket", "pathlib", "shutil", "requests", "urllib", "ctypes", "pickle", "marshal"}

    @classmethod
    def validate(cls, code: str) -> None:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                raise ValueError("imports are disabled in the preparation harness")
            if isinstance(node, ast.Name) and node.id in cls.BANNED_NAMES | cls.BANNED_MODULES:
                raise ValueError(f"blocked name: {node.id}")
            if isinstance(node, ast.Attribute) and node.value.__class__ is ast.Name and node.value.id in cls.BANNED_MODULES:
                raise ValueError(f"blocked module: {node.value.id}")
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
