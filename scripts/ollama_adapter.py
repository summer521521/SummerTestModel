"""Ollama HTTP transport with native-runtime and evidence-preserving telemetry."""
from __future__ import annotations

import datetime as dt
import json
import socket
import time
import urllib.error
import urllib.request
from typing import Any


SAMPLING_KEYS = (
    "temperature",
    "top_k",
    "top_p",
    "min_p",
    "typical_p",
    "repeat_penalty",
    "presence_penalty",
    "frequency_penalty",
    "seed",
)
SERVER_TIMING_KEYS = (
    "load_duration",
    "prompt_eval_count",
    "prompt_eval_duration",
    "eval_count",
    "eval_duration",
    "total_duration",
)


def _timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="milliseconds")


def _seconds(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value) / 1_000_000_000
    except (TypeError, ValueError):
        return None


class OllamaTransportError(RuntimeError):
    def __init__(self, status, message, retryable=False, meaningful=False, partial=None):
        super().__init__(message)
        self.status = status
        self.retryable = retryable
        self.meaningful = meaningful
        self.partial = partial or {}


class OllamaAdapter:
    def __init__(self, base_url="http://127.0.0.1:11434", max_transport_retries=1):
        self.base_url = base_url.rstrip("/")
        self.max_transport_retries = max_transport_retries

    @staticmethod
    def _options(profile, runtime_overrides=None, seed_supported=None):
        overrides = runtime_overrides if isinstance(runtime_overrides, dict) else {}
        options = {key: profile[key] for key in ("num_ctx", "num_predict") if key in profile}
        declared_sampling = False
        for key in SAMPLING_KEYS:
            if key in overrides:
                options[key] = overrides[key]
                declared_sampling = True
            elif key in profile:
                if key != "seed" or seed_supported is not False:
                    options[key] = profile[key]
                    declared_sampling = True
        applied = "seed" in options
        return options, {
            "seed_applied": applied,
            "seed_reason": "explicitly_declared" if applied else "not_declared",
            "sampling_override_present": declared_sampling,
        }

    @staticmethod
    def _think(profile, capabilities, runtime_overrides=None):
        overrides = runtime_overrides if isinstance(runtime_overrides, dict) else {}
        if "think" in overrides:
            return bool(overrides["think"]), "explicit_model_runtime_override"
        if "think" not in profile:
            return None, "unsupported_or_not_requested"
        requested = profile.get("think")
        if requested is False:
            return False, "explicit_profile_control"
        supports = "thinking" in set(capabilities or [])
        if not supports:
            return None, "native_content"
        return True, "explicit_profile_control"

    @staticmethod
    def _timing(
        *,
        started_mono: float,
        finished_mono: float,
        request_started_at: str,
        request_finished_at: str,
        first_chunk_at: str | None,
        first_generated_at: str | None,
        first_thinking_at: str | None,
        first_final_at: str | None,
        terminal_record_at: str | None,
        metadata: dict[str, Any],
        soft_limit: float | None,
    ) -> dict[str, Any]:
        def delta(stamp: str | None) -> float | None:
            if stamp is None:
                return None
            # The monotonic deltas are assigned by the caller for the current
            # request; timestamp fields remain the durable cross-process record.
            return None

        # The caller supplies monotonic offsets in the private helper fields.
        timing = {
            "request_started_at": request_started_at,
            "first_chunk_at": first_chunk_at,
            "first_generated_at": first_generated_at,
            "first_thinking_at": first_thinking_at,
            "first_final_at": first_final_at,
            "terminal_record_at": terminal_record_at,
            "request_finished_at": request_finished_at,
            "client_wall_seconds": finished_mono - started_mono,
            "time_to_first_chunk_seconds": metadata.pop("_time_to_first_chunk_seconds", None),
            "time_to_first_generated_seconds": metadata.pop("_time_to_first_generated_seconds", None),
            "time_to_first_thinking_seconds": metadata.pop("_time_to_first_thinking_seconds", None),
            "time_to_first_final_seconds": metadata.pop("_time_to_first_final_seconds", None),
        }
        timing["wall_time_seconds"] = timing["client_wall_seconds"]
        timing["time_to_first_token"] = timing["time_to_first_generated_seconds"]
        for key, value in metadata.items():
            timing[key] = value
        for key in SERVER_TIMING_KEYS:
            if key in metadata:
                seconds_key = f"{key}_seconds"
                if key.endswith("_duration"):
                    timing[seconds_key] = _seconds(metadata[key])
        if metadata.get("prompt_eval_count") is not None and metadata.get("prompt_eval_duration"):
            timing["prompt_tokens_per_second"] = metadata["prompt_eval_count"] / (metadata["prompt_eval_duration"] / 1e9)
        if metadata.get("eval_count") is not None and metadata.get("eval_duration"):
            timing["output_tokens_per_second"] = metadata["eval_count"] / (metadata["eval_duration"] / 1e9)
        timing["practical_within_soft_limit"] = soft_limit is None or timing["client_wall_seconds"] <= float(soft_limit)
        return timing

    def _post(self, endpoint, payload, inactivity, absolute, soft_limit=None, cancel_event=None, think_requested=None):
        started_mono = time.monotonic()
        request_started_at = _timestamp()
        first_chunk_mono = None
        first_generated_mono = None
        first_thinking_mono = None
        first_final_mono = None
        terminal_record_mono = None
        chunks: list[dict[str, Any]] = []
        thinking: list[str] = []
        answer: list[str] = []
        tool_calls: list[Any] = []
        metadata: dict[str, Any] = {}
        meaningful = False

        def partial(status: str, error: str | None = None) -> dict[str, Any]:
            finished_mono = time.monotonic()
            request_finished_at = _timestamp()
            offsets = {
                "_time_to_first_chunk_seconds": None if first_chunk_mono is None else first_chunk_mono - started_mono,
                "_time_to_first_generated_seconds": None if first_generated_mono is None else first_generated_mono - started_mono,
                "_time_to_first_thinking_seconds": None if first_thinking_mono is None else first_thinking_mono - started_mono,
                "_time_to_first_final_seconds": None if first_final_mono is None else first_final_mono - started_mono,
            }
            timing = self._timing(
                started_mono=started_mono,
                finished_mono=finished_mono,
                request_started_at=request_started_at,
                request_finished_at=request_finished_at,
                first_chunk_at=None if first_chunk_mono is None else _timestamp_for_elapsed(started_mono, first_chunk_mono, request_started_at),
                first_generated_at=None if first_generated_mono is None else _timestamp_for_elapsed(started_mono, first_generated_mono, request_started_at),
                first_thinking_at=None if first_thinking_mono is None else _timestamp_for_elapsed(started_mono, first_thinking_mono, request_started_at),
                first_final_at=None if first_final_mono is None else _timestamp_for_elapsed(started_mono, first_final_mono, request_started_at),
                terminal_record_at=None if terminal_record_mono is None else _timestamp_for_elapsed(started_mono, terminal_record_mono, request_started_at),
                metadata={**metadata, **offsets},
                soft_limit=soft_limit,
            )
            return {
                "status": status,
                "raw_response": chunks,
                "streamed_chunks": chunks,
                "thinking": "".join(thinking) or None,
                "final_answer": "".join(answer) or None,
                "tool_calls": tool_calls or None,
                "ollama_metadata": {key: value for key, value in metadata.items() if not key.startswith("_")},
                "timing": timing,
                "meaningful": meaningful,
                "terminal_record_seen": terminal_record_mono is not None,
                "completion_terminal_record": False,
                "runtime_anomaly": True,
                "request_started_at": request_started_at,
                "request_finished_at": request_finished_at,
                "finished_at": request_finished_at,
                "error": error,
            }

        request = urllib.request.Request(
            self.base_url + endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            response = urllib.request.urlopen(request, timeout=inactivity)
            saw_done = False
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    raise OllamaTransportError("cancelled", "cancelled", False, meaningful, partial("cancelled", "cancelled"))
                if time.monotonic() - started_mono > absolute:
                    raise OllamaTransportError("absolute_timeout", "absolute timeout", False, meaningful, partial("absolute_timeout", "absolute timeout"))
                line = response.readline()
                if not line:
                    break
                if first_chunk_mono is None:
                    first_chunk_mono = time.monotonic()
                try:
                    chunk = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    status = "stream_interrupted_after_output" if meaningful else "stream_interrupted_before_output"
                    raise OllamaTransportError(status, f"malformed NDJSON stream: {exc}", not meaningful, meaningful, partial(status, str(exc)))
                chunks.append(chunk)
                metadata.update({key: chunk[key] for key in SERVER_TIMING_KEYS if key in chunk})
                message = chunk.get("message") or {}
                t = message.get("thinking", chunk.get("thinking"))
                c = message.get("content", chunk.get("response"))
                calls = message.get("tool_calls") or chunk.get("tool_calls") or []
                if t:
                    if first_thinking_mono is None:
                        first_thinking_mono = time.monotonic()
                    thinking.append(str(t))
                    meaningful = True
                if c:
                    if first_final_mono is None:
                        first_final_mono = time.monotonic()
                    answer.append(str(c))
                    meaningful = True
                if calls:
                    tool_calls.extend(calls)
                    meaningful = True
                if meaningful and first_generated_mono is None:
                    first_generated_mono = min(x for x in (first_thinking_mono, first_final_mono, time.monotonic()) if x is not None)
                if chunk.get("done"):
                    saw_done = True
                    terminal_record_mono = time.monotonic()
                    break
            if not saw_done:
                status = "stream_interrupted_after_output" if meaningful else "stream_interrupted_before_output"
                raise OllamaTransportError(status, "stream ended before done", not meaningful, meaningful, partial(status, "stream ended before done"))
            finished_mono = time.monotonic()
            request_finished_at = _timestamp()
            final = "".join(answer)
            think = "".join(thinking)
            done_reason = chunks[-1].get("done_reason") if chunks else None
            status = "completed"
            if done_reason == "length" and not final:
                status = "truncated_before_final"
            elif done_reason == "length":
                status = "truncated"
            if not final and think_requested is True:
                status = "timeout_before_final" if not chunks else "truncated_before_final"
            offsets = {
                "_time_to_first_chunk_seconds": None if first_chunk_mono is None else first_chunk_mono - started_mono,
                "_time_to_first_generated_seconds": None if first_generated_mono is None else first_generated_mono - started_mono,
                "_time_to_first_thinking_seconds": None if first_thinking_mono is None else first_thinking_mono - started_mono,
                "_time_to_first_final_seconds": None if first_final_mono is None else first_final_mono - started_mono,
            }
            timing = self._timing(
                started_mono=started_mono,
                finished_mono=finished_mono,
                request_started_at=request_started_at if request_started_at else _timestamp(),
                request_finished_at=request_finished_at,
                first_chunk_at=None if first_chunk_mono is None else _timestamp_for_elapsed(started_mono, first_chunk_mono, request_started_at),
                first_generated_at=None if first_generated_mono is None else _timestamp_for_elapsed(started_mono, first_generated_mono, request_started_at),
                first_thinking_at=None if first_thinking_mono is None else _timestamp_for_elapsed(started_mono, first_thinking_mono, request_started_at),
                first_final_at=None if first_final_mono is None else _timestamp_for_elapsed(started_mono, first_final_mono, request_started_at),
                terminal_record_at=_timestamp_for_elapsed(started_mono, terminal_record_mono, request_started_at),
                metadata={**metadata, **offsets},
                soft_limit=soft_limit,
            )
            return {
                "status": status,
                "raw_response": chunks,
                "streamed_chunks": chunks,
                "thinking": think or None,
                "final_answer": final or None,
                "tool_calls": tool_calls or None,
                "ollama_metadata": metadata,
                "termination_reason": done_reason,
                "done_reason": done_reason,
                "timing": timing,
                "meaningful": meaningful,
                "terminal_record_seen": True,
                "completion_terminal_record": True,
                "runtime_anomaly": False,
                "request_started_at": request_started_at,
                "request_finished_at": request_finished_at,
                "finished_at": request_finished_at,
            }
        except OllamaTransportError:
            raise
        except urllib.error.HTTPError as exc:
            code = exc.code
            retry = code in {500, 502, 503, 504}
            raise OllamaTransportError(f"http_{code}", f"HTTP {code}", retry, meaningful, partial(f"http_{code}", f"HTTP {code}"))
        except socket.timeout as exc:
            raise OllamaTransportError("inactivity_timeout", f"socket.timeout: {exc}", False, meaningful, partial("inactivity_timeout", str(exc)))
        except (ConnectionRefusedError, ConnectionResetError, urllib.error.URLError) as exc:
            reason = getattr(exc, "reason", exc)
            text = str(reason).lower()
            refused = isinstance(exc, ConnectionRefusedError) or "refused" in text
            status = "connection_refused" if refused else ("stream_interrupted_after_output" if meaningful else "stream_interrupted_before_output")
            raise OllamaTransportError(status, f"{type(exc).__name__}: {exc}", not meaningful, meaningful, partial(status, str(exc)))

    def _infer_stream(self, item):
        profile = dict(item.get("profile_config") or {})
        caps = item.get("capabilities") or item.get("metadata_capabilities") or []
        options, seed_info = self._options(profile, item.get("runtime_overrides"), item.get("seed_supported"))
        think, think_reason = self._think(profile, caps, item.get("runtime_overrides"))
        payload = {
            "model": item["model"],
            "stream": True,
            "options": options,
            "keep_alive": profile.get("keep_alive_seconds", 300),
        }
        if item.get("messages") is not None:
            payload["messages"] = item["messages"]
        else:
            payload["prompt"] = item.get("prompt", "")
            if item.get("images") is not None:
                payload["images"] = item["images"]
        if item.get("tools") is not None:
            payload["tools"] = item["tools"]
        if think is not None:
            payload["think"] = think
        endpoint = "/api/chat" if item.get("messages") is not None else "/api/generate"
        attempts = []
        for attempt in range(self.max_transport_retries + 1):
            try:
                result = self._post(
                    endpoint,
                    payload,
                    profile.get("inactivity_timeout_seconds", 180),
                    profile.get("absolute_timeout_seconds", 600),
                    profile.get("practical_soft_limit_seconds"),
                    item.get("cancel_event"),
                    think,
                )
                result.update({
                    "request_payload": payload,
                    "endpoint": endpoint,
                    "transport_attempts": attempts,
                    "think_reason": think_reason,
                    "reasoning_mode": "native_content" if profile.get("think") is True and think is None else "requested_thinking" if think is True else "standard_content",
                    "sampling_policy": item.get("sampling_policy", "native_artifact"),
                    "retryable": False,
                    "meaningful": bool(result.get("meaningful")),
                    **seed_info,
                })
                return result
            except OllamaTransportError as exc:
                attempts.append({"attempt": attempt + 1, "status": exc.status, "error": str(exc)})
                if not exc.retryable or exc.meaningful or attempt >= self.max_transport_retries:
                    result = dict(exc.partial)
                    result.update({
                        "status": exc.status,
                        "request_payload": payload,
                        "endpoint": endpoint,
                        "transport_attempts": attempts,
                        "think_reason": think_reason,
                        "reasoning_mode": "native_content" if profile.get("think") is True and think is None else "requested_thinking" if think is True else "standard_content",
                        "sampling_policy": item.get("sampling_policy", "native_artifact"),
                        "retryable": exc.retryable,
                        "meaningful": bool(result.get("meaningful")),
                        **seed_info,
                    })
                    return result
        return {"status": "runner_exception", "request_payload": payload, "sampling_policy": item.get("sampling_policy", "native_artifact")}

    def infer(self, item):
        return self._infer_stream(item)

    def preload(self, model, keep_alive="5m", ollama_version=None):
        payload = {"model": model, "keep_alive": keep_alive}
        started_mono = time.monotonic()
        started_at = _timestamp()
        request = urllib.request.Request(
            self.base_url + "/api/generate",
            data=json.dumps(payload, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = response.read()
                metadata = json.loads(body.decode("utf-8")) if body else {}
                if not isinstance(metadata, dict):
                    metadata = {}
                finished_at = _timestamp()
                timing = {
                    "request_started_at": started_at,
                    "request_finished_at": finished_at,
                    "client_wall_seconds": time.monotonic() - started_mono,
                    "load_duration": metadata.get("load_duration"),
                    "total_duration": metadata.get("total_duration"),
                    "load_duration_seconds": _seconds(metadata.get("load_duration")),
                    "total_duration_seconds": _seconds(metadata.get("total_duration")),
                }
                return {
                    "status": "completed" if getattr(response, "status", 200) == 200 else f"http_{getattr(response, 'status', 0)}",
                    "model": model,
                    "request_payload": payload,
                    "request_started_at": started_at,
                    "request_finished_at": finished_at,
                    "client_wall_seconds": timing["client_wall_seconds"],
                    "load_duration": metadata.get("load_duration"),
                    "total_duration": metadata.get("total_duration"),
                    "timing": timing,
                    "ollama_metadata": metadata,
                    "ollama_version": ollama_version,
                }
        except urllib.error.HTTPError as exc:
            return {"status": f"http_{exc.code}", "model": model, "request_payload": payload, "request_started_at": started_at, "request_finished_at": _timestamp(), "error": f"HTTP {exc.code}"}
        except (ConnectionRefusedError, ConnectionResetError, urllib.error.URLError, socket.timeout) as exc:
            return {"status": "connection_refused" if "refused" in str(exc).lower() or isinstance(exc, ConnectionRefusedError) else "preload_error", "model": model, "request_payload": payload, "request_started_at": started_at, "request_finished_at": _timestamp(), "error": f"{type(exc).__name__}: {exc}"}

    def embed(self, model, inputs, profile=None):
        profile = profile or {}
        payload = {"model": model, "input": inputs, "keep_alive": profile.get("keep_alive_seconds", 300)}
        started_mono = time.monotonic()
        started_at = _timestamp()
        request = urllib.request.Request(
            self.base_url + "/api/embed",
            data=json.dumps(payload, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=profile.get("inactivity_timeout_seconds", 120)) as response:
                value = json.loads(response.read().decode("utf-8"))
                finished_at = _timestamp()
                metadata = value if isinstance(value, dict) else {}
                timing = {
                    "request_started_at": started_at,
                    "first_chunk_at": started_at,
                    "first_generated_at": None,
                    "first_thinking_at": None,
                    "first_final_at": None,
                    "terminal_record_at": finished_at,
                    "request_finished_at": finished_at,
                    "client_wall_seconds": time.monotonic() - started_mono,
                    "time_to_first_chunk_seconds": 0.0,
                    "time_to_first_generated_seconds": None,
                    "time_to_first_thinking_seconds": None,
                    "time_to_first_final_seconds": None,
                    "practical_within_soft_limit": time.monotonic() - started_mono <= float(profile.get("practical_soft_limit_seconds", 120)),
                }
                for key in SERVER_TIMING_KEYS:
                    if key in metadata:
                        timing[key] = metadata[key]
                        if key.endswith("_duration"):
                            timing[f"{key}_seconds"] = _seconds(metadata[key])
                return {
                    "status": "completed",
                    "request_payload": payload,
                    "final_answer": None,
                    "embedding": metadata.get("embeddings") or metadata.get("embedding"),
                    "ollama_metadata": metadata,
                    "timing": timing,
                    "terminal_record_seen": True,
                    "completion_terminal_record": True,
                    "runtime_anomaly": False,
                    "finished_at": finished_at,
                    "sampling_policy": "native_artifact",
                }
        except Exception as exc:
            status = "connection_refused" if isinstance(exc, ConnectionRefusedError) or "refused" in str(exc).lower() else "embed_error"
            finished_at = _timestamp()
            return {
                "status": status,
                "request_payload": payload,
                "error": f"{type(exc).__name__}: {exc}",
                "finished_at": finished_at,
                "timing": {"request_started_at": started_at, "request_finished_at": finished_at, "client_wall_seconds": time.monotonic() - started_mono},
                "sampling_policy": "native_artifact",
            }

    def unload(self, model):
        payload = {"model": model, "prompt": "", "stream": False, "keep_alive": 0}
        request = urllib.request.Request(
            self.base_url + "/api/generate",
            data=json.dumps(payload, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status == 200


def _timestamp_for_elapsed(start_mono: float, event_mono: float, started_at: str) -> str:
    """Return a durable timestamp using the monotonic offset of the event."""
    try:
        parsed = dt.datetime.fromisoformat(started_at)
        return (parsed + dt.timedelta(seconds=event_mono - start_mono)).isoformat(timespec="milliseconds")
    except ValueError:
        return _timestamp()
