"""Deterministic Ollama HTTP adapter; no benchmark tasks or scorers are embedded."""
from __future__ import annotations
import json, socket, time, urllib.error, urllib.request
from typing import Any

class OllamaTransportError(RuntimeError):
    def __init__(self, status, message, retryable=False, meaningful=False):
        super().__init__(message); self.status = status; self.retryable = retryable; self.meaningful = meaningful

class OllamaAdapter:
    def __init__(self, base_url="http://127.0.0.1:11434", max_transport_retries=1):
        self.base_url = base_url.rstrip("/"); self.max_transport_retries = max_transport_retries

    @staticmethod
    def _options(profile, seed_supported=None):
        options = {k: profile[k] for k in ("temperature", "num_ctx", "num_predict") if k in profile}
        applied = False
        if seed_supported is True and "seed" in profile:
            options["seed"] = profile["seed"]; applied = True
        return options, {"seed_applied": applied, "seed_reason": "verified" if applied else "not_verified"}

    @staticmethod
    def _think(profile, capabilities, runtime_overrides=None):
        overrides = runtime_overrides if isinstance(runtime_overrides, dict) else {}
        if "think" in overrides:
            return bool(overrides["think"]), "explicit_model_runtime_override"
        supports = "thinking" in set(capabilities or [])
        requested = profile.get("think")
        if requested is None or not supports: return None, "unsupported_or_not_requested"
        return bool(requested), "explicit_profile_control"

    def _post(self, endpoint, payload, inactivity, absolute, cancel_event=None, think_requested=None):
        started = time.monotonic(); first_token_at=None; chunks=[]; thinking=[]; answer=[]; tool_calls=[]; metadata={}; meaningful=False
        request = urllib.request.Request(self.base_url + endpoint, data=json.dumps(payload, ensure_ascii=False).encode(), headers={"Content-Type":"application/json"}, method="POST")
        try:
            response = urllib.request.urlopen(request, timeout=inactivity)
            saw_done = False
            while True:
                if cancel_event is not None and cancel_event.is_set(): raise OllamaTransportError("cancelled", "cancelled")
                if time.monotonic() - started > absolute: raise OllamaTransportError("absolute_timeout", "absolute timeout")
                line = response.readline()
                if not line: break
                try: chunk = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError: raise OllamaTransportError("stream_interrupted", "malformed NDJSON stream", True, meaningful)
                chunks.append(chunk); metadata.update({k: chunk[k] for k in ("load_duration","prompt_eval_count","prompt_eval_duration","eval_count","eval_duration","total_duration") if k in chunk})
                msg = chunk.get("message") or {}
                t = msg.get("thinking", chunk.get("thinking")); c = msg.get("content", chunk.get("response"))
                if t: thinking.append(str(t)); meaningful = True
                if c: answer.append(str(c)); meaningful = True
                calls = msg.get("tool_calls") or chunk.get("tool_calls") or []
                if calls: tool_calls.extend(calls); meaningful = True
                if meaningful and first_token_at is None: first_token_at = time.monotonic()
                if chunk.get("done"):
                    saw_done = True
                    break
            if not saw_done:
                raise OllamaTransportError("stream_interrupted", "stream ended before done", not meaningful, meaningful)
            finished = time.monotonic()
            final = "".join(answer); think = "".join(thinking)
            done_reason = chunks[-1].get("done_reason") if chunks else None
            status = "completed"
            if done_reason == "length" and not final: status = "truncated_before_final"
            elif done_reason == "length": status = "truncated"
            if not final and think_requested is True: status = "timeout_before_final" if not chunks else "truncated_before_final"
            timing={"wall_time_seconds":finished-started,"time_to_first_token":None if first_token_at is None else first_token_at-started, **metadata}
            if metadata.get("prompt_eval_count") is not None and metadata.get("prompt_eval_duration"):
                timing["prompt_tokens_per_second"] = metadata["prompt_eval_count"] / (metadata["prompt_eval_duration"] / 1e9)
            if metadata.get("eval_count") is not None and metadata.get("eval_duration"):
                timing["output_tokens_per_second"] = metadata["eval_count"] / (metadata["eval_duration"] / 1e9)
            return {"status":status,"raw_response":chunks,"streamed_chunks":chunks,"thinking":think or None,"final_answer":final or None,"tool_calls":tool_calls or None,"ollama_metadata":metadata,"termination_reason":done_reason,"timing":timing,"meaningful":meaningful}
        except urllib.error.HTTPError as exc:
            code = exc.code; retry = code in {500,502,503,504}
            raise OllamaTransportError(f"http_{code}", f"HTTP {code}", retry, meaningful)
        except socket.timeout as exc:
            raise OllamaTransportError("inactivity_timeout", f"socket.timeout: {exc}", False, meaningful)
        except (ConnectionRefusedError, ConnectionResetError, urllib.error.URLError) as exc:
            reason = getattr(exc, "reason", exc); text = str(reason).lower()
            refused = isinstance(exc, ConnectionRefusedError) or "refused" in text
            status = "connection_refused" if refused else "stream_interrupted"
            raise OllamaTransportError(status, f"{type(exc).__name__}: {exc}", True and not meaningful, meaningful)

    def _infer_stream(self, item):
        profile = dict(item.get("profile_config") or {})
        caps = item.get("capabilities") or item.get("metadata_capabilities") or []
        options, seed_info = self._options({**profile, "temperature":0, "seed":42}, item.get("seed_supported"))
        think, think_reason = self._think(profile, caps, item.get("runtime_overrides"))
        payload = {"model": item["model"], "stream": True, "options": options, "keep_alive": profile.get("keep_alive_seconds", 300)}
        if item.get("messages") is not None:
            payload["messages"] = item["messages"]
        else:
            payload["prompt"] = item.get("prompt", "")
            if item.get("images") is not None: payload["images"] = item["images"]
        if item.get("tools") is not None: payload["tools"] = item["tools"]
        if think is not None: payload["think"] = think
        endpoint = "/api/chat" if item.get("messages") is not None else "/api/generate"
        attempts=[]
        for attempt in range(self.max_transport_retries + 1):
            try:
                result = self._post(endpoint, payload, profile.get("inactivity_timeout_seconds",60), profile.get("absolute_timeout_seconds",180), item.get("cancel_event"), think)
                result.update({"request_payload":payload,"endpoint":endpoint,"transport_attempts":attempts,"think_reason":think_reason,**seed_info}); return result
            except OllamaTransportError as exc:
                attempts.append({"attempt":attempt+1,"status":exc.status,"error":str(exc)})
                if not exc.retryable or exc.meaningful or attempt >= self.max_transport_retries:
                    return {"status":exc.status,"request_payload":payload,"endpoint":endpoint,"transport_attempts":attempts,"error":str(exc),"think_reason":think_reason,**seed_info}

    def infer(self, item):
        return self._infer_stream(item)

    def embed(self, model, inputs, profile=None):
        profile = profile or {}; payload={"model":model,"input":inputs,"keep_alive":profile.get("keep_alive_seconds",300)}
        try:
            response = urllib.request.urlopen(urllib.request.Request(self.base_url+"/api/embed", data=json.dumps(payload).encode(), headers={"Content-Type":"application/json"}), timeout=profile.get("inactivity_timeout_seconds",30))
            value=json.loads(response.read().decode("utf-8")); return {"status":"completed","request_payload":payload,"final_answer":None,"embedding":value.get("embeddings") or value.get("embedding"),"ollama_metadata":value}
        except Exception as exc: return {"status":"connection_refused" if isinstance(exc, ConnectionRefusedError) else "embed_error","request_payload":payload,"error":f"{type(exc).__name__}: {exc}"}

    def unload(self, model):
        payload={"model":model,"prompt":"","stream":False,"keep_alive":0}
        request=urllib.request.Request(self.base_url+"/api/generate",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(request, timeout=10) as response: return response.status == 200
