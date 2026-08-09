"""Mechanical entry point for the frozen SummerTestModel Benchmark 1.0 RC1.

This module wires existing adapter, persistence, tool-loop, and scorer code. It
does not contain prompts, answers, scoring rules, or model-selection policy.
Real calibration and inference are deliberately gated; use ``--mock`` only
for the offline integration path.
"""
from __future__ import annotations

import argparse
import base64
import copy
import datetime as dt
import importlib
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.executor_core import (
    INFRA_FAILURE,
    TERMINAL_INFERENCE,
    CircuitBreaker,
    CircuitConfig,
    EvidenceStore,
    Executor,
    append_jsonl,
    logical_key,
    now,
)
from scripts.ollama_adapter import OllamaAdapter
from scripts.tool_loop import ToolLoopEngine
from scripts.luna_executor import doctor as luna_doctor, healthcheck, status as luna_status

CONFIG_DIR = ROOT / "config"
PRIVATE = ROOT / "private_benchmark" / "1.0-rc1"
DEFAULT_CONFIG = CONFIG_DIR / "run_config.template.json"
DEFAULT_RUN_ROOT = ROOT / "private_runs"
R2_CALIBRATION_PLAN = CONFIG_DIR / "calibration_plan.rc1.r2.json"
R3_CALIBRATION_PLAN = CONFIG_DIR / "calibration_plan.rc1.r3.json"
R3_CALIBRATION_PLAN = CONFIG_DIR / "calibration_plan.rc1.r3.json"


def read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def config_bundle(config_path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config = read(config_path)
    benchmark = read(ROOT / config["benchmark_manifest"])
    task_manifest = read(ROOT / config["task_manifest"])
    scorer_manifest = read(ROOT / config["scorer_manifest"])
    plan = read(ROOT / config["model_execution_plan"])
    profiles = read(ROOT / config["generation_profiles"])
    retry = read(ROOT / config["retry_policy"])
    inventory = read(ROOT / config["inventory_path"])
    runtime_defaults_path = ROOT / str(config.get("model_runtime_defaults") or "inventory/model_runtime_defaults.rc1.json")
    runtime_defaults = read(runtime_defaults_path) if runtime_defaults_path.is_file() else {"models": []}
    return {"config": config, "benchmark": benchmark, "tasks": task_manifest,
            "scorers": scorer_manifest, "plan": plan, "profiles": profiles,
            "retry": retry, "inventory": inventory, "runtime_defaults": runtime_defaults}


class FormalScorer:
    """Load private task payloads and dispatch through the public scorer entrypoint."""

    def __init__(self, bundle: dict[str, Any]):
        self.bundle = bundle
        self.task_manifest = {x["task_id"]: x for x in bundle["tasks"]["tasks"]}
        self.scorers = {x["scorer_id"]: x for x in bundle["scorers"]["scorers"]}

    def score(self, evidence: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
        public_task = self.task_manifest.get(item["task_id"])
        if public_task is None and item.get("task_id") == "PERF_01":
            # Historical R2 compatibility only. PERF_01 is intentionally not
            # present in the R3 formal task manifest.
            public_task = {"task_id": "PERF_01", "track": "performance", "scorer_id": "performance_telemetry_v1"}
        if public_task is None:
            raise KeyError(item["task_id"])
        scorer_id = public_task["scorer_id"]
        manifest_entry = self.scorers.get(scorer_id)
        if not manifest_entry or manifest_entry["track"] != public_task["track"]:
            raise ValueError(f"scorer referential mismatch: {item['task_id']}:{scorer_id}")
        implementation = manifest_entry["implementation"]
        module_name, function_name = implementation.split(":", 1)
        module_name = module_name[:-3].replace("/", ".").replace("\\", ".")
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            module = importlib.import_module(module_name.rsplit(".", 1)[-1])
        function = getattr(module, function_name, None)
        if not callable(function):
            raise ImportError(f"scorer entrypoint unavailable: {implementation}")
        task = read(PRIVATE / "tasks" / f"{item['task_id']}.json")
        ground_truth = read(PRIVATE / "ground_truth" / f"{item['task_id']}.json")
        scoring_spec = read(PRIVATE / "scoring_specs" / f"{item['task_id']}.json")
        return function(evidence, task, ground_truth, scoring_spec)


def _asset_for(task_id: str, public_task: dict[str, Any]) -> tuple[list[str], list[str]]:
    images: list[str] = []
    paths: list[str] = []
    for declared in public_task.get("assets") or []:
        path = PRIVATE / declared["path"]
        if not path.is_file():
            raise FileNotFoundError(path)
        images.append(base64.b64encode(path.read_bytes()).decode("ascii"))
        paths.append(path.relative_to(PRIVATE).as_posix())
    return images, paths


class RC1ItemBuilder:
    def __init__(self, bundle: dict[str, Any]):
        self.bundle = bundle
        self.tasks = {x["task_id"]: x for x in bundle["tasks"]["tasks"]}
        self.inventory = {x["exact_name"]: x for x in bundle["inventory"]["models"]}
        self.runtime_defaults = {x["exact_name"]: x for x in bundle.get("runtime_defaults", {}).get("models", [])}
        self.private_tasks = {p.stem: read(p) for p in (PRIVATE / "tasks").glob("*.json")}
        self.tool_fixtures = {x["task_id"]: x for x in read(PRIVATE / "tool_fixtures" / "tasks.json")}
        self.tools = read(PRIVATE / "tool_fixtures" / "tools.json").get("tools", [])
        self.embedding_docs = read(PRIVATE / "embedding" / "corpus.json")
        self.embedding_queries = {x["query_id"]: x for x in read(PRIVATE / "embedding" / "queries.json")}

    def build(self, model_row: dict[str, Any], task_id: str) -> dict[str, Any]:
        public_task = self.tasks[task_id]
        private_task = self.private_tasks[task_id]
        metadata = self.inventory[model_row["model"]]
        profile = public_task["profile"]
        profile_config = copy.deepcopy(self.bundle["profiles"]["profiles"][profile])
        runtime_overrides = copy.deepcopy(
            (self.bundle["profiles"].get("model_runtime_overrides") or {}).get(model_row["model"], {})
        )
        sampling_keys = {"temperature", "top_k", "top_p", "min_p", "typical_p", "repeat_penalty", "presence_penalty", "frequency_penalty", "seed"}
        sampling_policy = "architect_model_override" if runtime_overrides else "native_artifact"
        runtime_snapshot = self.runtime_defaults.get(model_row["model"], {})
        supports_thinking = "thinking" in set(metadata.get("capabilities") or [])
        item = {
            "benchmark_version": self.bundle["benchmark"]["benchmark_version"],
            "task_manifest_hash": self.bundle["config"]["manifest_hashes"]["task_manifest"],
            "scorer_version": self.bundle["config"]["scorer_version"],
            "model": model_row["model"], "exact_model_tag": model_row["model"],
            "model_digest": model_row["digest"], "task_id": task_id,
            "track": public_task["track"], "profile": profile,
            "profile_config": profile_config,
            "capabilities": list(metadata.get("capabilities") or []),
            "prompt": private_task.get("prompt", ""),
            "scorer_id": public_task["scorer_id"],
            "task_version": private_task.get("version", self.bundle["benchmark"]["benchmark_version"]),
            "ollama_version": self.bundle["inventory"].get("ollama_version"),
            "machine_profile_hash": self.bundle["config"].get("machine_profile_hash"),
            "seed_supported": None,
            "sampling_policy": sampling_policy,
            "runtime_defaults_snapshot_hash": self.bundle["config"].get("manifest_hashes", {}).get("model_runtime_defaults"),
            "model_modelfile_sha256": runtime_snapshot.get("modelfile_sha256"),
            "reasoning_mode": "requested_thinking" if profile_config.get("think") is True and supports_thinking else "native_content" if profile_config.get("think") is True else "standard_content",
        }
        if runtime_overrides:
            item["runtime_overrides"] = runtime_overrides
        if public_task["track"] in {"vision", "ocr"}:
            images, paths = _asset_for(task_id, public_task)
            item["images"] = images
            item["asset_paths"] = paths
            item["messages"] = [{"role": "user", "content": item["prompt"], "images": images}]
        elif public_task["track"] in {"tools", "safety"}:
            item["messages"] = [{"role": "user", "content": item["prompt"]}]
        if public_task["track"] == "tools":
            item["tool_definitions"] = self.tools
            item["tools"] = [
                {"type":"function","function":{"name":tool["name"],"description":tool.get("description", ""),"parameters":tool["arguments_schema"]}}
                for tool in self.tools
            ]
            item["tool_fixture"] = self.tool_fixtures[task_id]
        if public_task["track"] == "embedding":
            query = self.embedding_queries[task_id.replace("EMB_", "")]
            item["embedding_corpus"] = self.embedding_docs
            item["embedding_query"] = query
            item["prompt"] = query["text"]
        if public_task["track"] == "code":
            item["requested_function"] = read(PRIVATE / "scoring_specs" / f"{task_id}.json").get("function")
        return item

    def all_items(self, selected_model: str | None = None, selected_task: str | None = None) -> list[dict[str, Any]]:
        items=[]
        for model_row in self.bundle["plan"]["models"]:
            if model_row.get("local_or_cloud") != "local" or (selected_model and model_row["model"] != selected_model):
                continue
            for task_id in model_row.get("task_ids") or []:
                if selected_task and task_id != selected_task: continue
                items.append(self.build(model_row, task_id))
        return items


class MockAdapter:
    """Deterministic protocol fixture. It never contacts Ollama."""

    def infer(self, item: dict[str, Any]) -> dict[str, Any]:
        track=item["track"]; profile=item["profile_config"]
        payload={"model":item["model"],"stream":True,"options":{key:profile.get(key) for key in ("num_ctx","num_predict") if profile.get(key) is not None}}
        requested_think=(item.get("runtime_overrides") or {}).get("think", profile.get("think"))
        if requested_think is True and "thinking" not in set(item.get("capabilities") or []) and not item.get("runtime_overrides"):
            requested_think = None
        if requested_think is not None: payload["think"]=bool(requested_think)
        if item.get("messages") is not None: payload["messages"]=item["messages"]
        else: payload["prompt"]=item.get("prompt","")
        if item.get("images") is not None: payload["images"]=item["images"]
        thinking="mock thinking" if profile.get("think") is True else None
        if item.get("calibration_probe"): answer="4"
        elif track == "code": answer=f"def {item.get('requested_function','mock_function')}(*args, **kwargs):\n    return None\n"
        elif track == "safety" and "guardian" in item["model"].lower(): answer="<score> no </score>"
        elif track == "safety": answer="No"
        else: answer="mock final answer"
        stamp=now()
        metadata={"load_duration":1000000,"prompt_eval_count":16,"prompt_eval_duration":1000000,"eval_count":256 if track=="performance" else 32,"eval_duration":1000000,"total_duration":3000000} if track=="performance" else {}
        return {"status":"completed","raw_response":[{"message":{"thinking":thinking,"content":answer},"done":True,"done_reason":"stop"}],"streamed_chunks":[{"message":{"thinking":thinking,"content":answer},"done":True,"done_reason":"stop"}],"thinking":thinking,"final_answer":answer,"request_payload":payload,"think_reason":"explicit_model_runtime_override" if item.get("runtime_overrides") else "explicit_profile_control" if profile.get("think") is not None else "unsupported_or_not_requested","endpoint":"mock","ollama_metadata":metadata,"timing":{"request_started_at":stamp,"first_chunk_at":stamp,"first_generated_at":stamp,"first_thinking_at":stamp if thinking else None,"first_final_at":stamp,"terminal_record_at":stamp,"request_finished_at":stamp,"client_wall_seconds":0.001,"wall_time_seconds":0.001,"time_to_first_chunk_seconds":0.001,"time_to_first_generated_seconds":0.001,"time_to_first_thinking_seconds":0.001 if thinking else None,"time_to_first_final_seconds":0.001,"practical_within_soft_limit":True},"request_started_at":stamp,"request_finished_at":stamp,"terminal_record_seen":True,"completion_terminal_record":True,"runtime_anomaly":False,"done_reason":"stop","reasoning_mode":item.get("reasoning_mode","standard_content"),"sampling_policy":item.get("sampling_policy","native_artifact"),"meaningful":True,"retryable":False,"images_sent":item.get("images")}


def _tool_call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {"type":"function","function":{"name":name,"arguments":arguments}}


def _normal_call(call: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    fn=call.get("function") or call
    args=fn.get("arguments",{})
    if isinstance(args,str): args=json.loads(args)
    return fn.get("name") or call.get("name"), args


class RC1Adapter:
    def __init__(self, base: Any, mock: bool = False): self.base, self.mock, self.current_model, self.pending_preload = base, mock, None, None

    def infer(self, item: dict[str, Any]) -> dict[str, Any]:
        if self.current_model != item["model"]:
            unload_record = None
            if not self.mock and self.current_model:
                unload_started = now()
                try:
                    unloaded = bool(self.base.unload(self.current_model))
                    unload_record = {"model": self.current_model, "status": "completed" if unloaded else "failed", "at": unload_started}
                except Exception as exc:
                    unload_record = {"model": self.current_model, "status": "error", "at": unload_started, "error": f"{type(exc).__name__}: {exc}"}
            self.current_model=item["model"]
            if self.mock:
                stamp = now()
                self.pending_preload = {"status":"completed","model":item["model"],"request_payload":{"model":item["model"],"keep_alive":"5m"},"request_started_at":stamp,"request_finished_at":stamp,"client_wall_seconds":0.001,"load_duration":1000000,"total_duration":2000000,"timing":{"request_started_at":stamp,"request_finished_at":stamp,"client_wall_seconds":0.001,"load_duration":1000000,"total_duration":2000000,"load_duration_seconds":0.001,"total_duration_seconds":0.002},"ollama_metadata":{"load_duration":1000000,"total_duration":2000000},"ollama_version":item.get("ollama_version")}
            else:
                self.pending_preload = self.base.preload(item["model"], "5m", item.get("ollama_version"))
            if isinstance(self.pending_preload, dict):
                self.pending_preload["model_digest"] = item.get("model_digest")
            if unload_record is not None:
                self.pending_preload["unload_previous"] = unload_record
        if item["track"] == "embedding": response = self._embedding(item)
        elif item["track"] == "tools": response = self._tools(item)
        else: response = self.base.infer(item)
        if self.pending_preload is not None:
            response = {**response, "preload": self.pending_preload}
            self.pending_preload = None
        response.setdefault("sampling_policy", item.get("sampling_policy", "native_artifact"))
        response.setdefault("reasoning_mode", item.get("reasoning_mode"))
        return response

    def close(self):
        if not self.mock and self.current_model:
            try:
                self.base.unload(self.current_model)
            finally:
                self.current_model = None

    def _embedding(self, item: dict[str, Any]) -> dict[str, Any]:
        if self.mock:
            docs=item["embedding_corpus"]; query=item["embedding_query"]
            relevant=query["relevant_doc_ids"][0]
            corpus={d["doc_id"]:([1.0,0.0] if d["doc_id"]==relevant else [0.0,1.0]) for d in docs}
            stamp=now()
            return {"status":"completed","embedding_corpus":corpus,"corpus_embeddings":corpus,"embedding":[1.0,0.0],"query_embedding":[1.0,0.0],"final_answer":None,"request_payload":{"endpoint":"/api/embed","input_count":len(docs)+1},"timing":{"request_started_at":stamp,"first_chunk_at":stamp,"first_generated_at":None,"first_thinking_at":None,"first_final_at":None,"terminal_record_at":stamp,"request_finished_at":stamp,"client_wall_seconds":0.001,"time_to_first_chunk_seconds":0.001,"time_to_first_generated_seconds":None,"time_to_first_thinking_seconds":None,"time_to_first_final_seconds":None,"wall_time_seconds":0.001,"practical_within_soft_limit":True},"terminal_record_seen":True,"completion_terminal_record":True,"sampling_policy":item.get("sampling_policy","native_artifact")}
        corpus_result=self.base.embed(item["model"],[d["text"] for d in item["embedding_corpus"]],item["profile_config"])
        query_result=self.base.embed(item["model"],item["embedding_query"]["text"],item["profile_config"])
        vectors=corpus_result.get("embedding") or []; query=query_result.get("embedding") or []
        if query and isinstance(query[0],list): query=query[0]
        if vectors and isinstance(vectors[0],list): corpus=dict(zip((d["doc_id"] for d in item["embedding_corpus"]),vectors))
        else: corpus={}
        first_timing=corpus_result.get("timing") or {}; query_timing=query_result.get("timing") or {}
        timing={"request_started_at":first_timing.get("request_started_at"),"first_chunk_at":first_timing.get("first_chunk_at"),"first_generated_at":None,"first_thinking_at":None,"first_final_at":None,"terminal_record_at":query_timing.get("terminal_record_at") or query_timing.get("request_finished_at"),"request_finished_at":query_timing.get("request_finished_at"),"client_wall_seconds":float(first_timing.get("client_wall_seconds") or 0)+float(query_timing.get("client_wall_seconds") or 0),"time_to_first_chunk_seconds":first_timing.get("time_to_first_chunk_seconds"),"time_to_first_generated_seconds":None,"time_to_first_thinking_seconds":None,"time_to_first_final_seconds":None,"practical_within_soft_limit":bool(first_timing.get("practical_within_soft_limit",True) and query_timing.get("practical_within_soft_limit",True))}
        return {"status":"completed" if corpus and query else corpus_result.get("status","embed_error"),"embedding_corpus":corpus,"corpus_embeddings":corpus,"embedding":query,"query_embedding":query,"final_answer":None,"request_payload":{"corpus":corpus_result.get("request_payload"),"query":query_result.get("request_payload")},"ollama_metadata":{"corpus":corpus_result.get("ollama_metadata"),"query":query_result.get("ollama_metadata")},"timing":timing,"terminal_record_seen":bool(corpus_result.get("terminal_record_seen") and query_result.get("terminal_record_seen")),"completion_terminal_record":bool(corpus_result.get("completion_terminal_record") and query_result.get("completion_terminal_record")),"sampling_policy":item.get("sampling_policy","native_artifact")}

    def _tools(self, item: dict[str, Any]) -> dict[str, Any]:
        expected=item["tool_fixture"]; calls=expected.get("expected_calls",[])
        turn_evidence=[]
        if self.mock:
            index=0
            def assistant(history):
                nonlocal index
                if expected.get("zero_call_required") or index>=len(calls):
                    return {"content":" ".join(expected.get("required_final_facts",[]) + (expected.get("required_final_any_of",[])[:1] if expected.get("required_final_any_of") else [])),"tool_calls":[]}
                call=calls[index]; index+=1; return {"content":None,"tool_calls":[_tool_call(call["name"],call["arguments"])]}
        else:
            def assistant(history):
                response=self.base.infer({**item,"messages":history})
                turn_evidence.append(response)
                return {"content":response.get("final_answer"),"tool_calls":response.get("tool_calls") or []}
        definitions={tool["name"]:tool for tool in item.get("tool_definitions",[])}
        def execute(name,args):
            definition=definitions[name]; schema=definition.get("arguments_schema",{}); properties=schema.get("properties",{}); required=schema.get("required",[])
            if any(key not in args for key in required) or (schema.get("additionalProperties") is False and any(key not in properties for key in args)): return json.dumps({"error":"invalid_arguments"})
            python_types={"string":str,"number":(int,float),"integer":int,"boolean":bool,"array":list,"object":dict}
            for key,value in args.items():
                expected_type=python_types.get((properties.get(key) or {}).get("type"))
                if expected_type and (not isinstance(value,expected_type) or isinstance(value,bool) and expected_type in {(int,float),int}):
                    return json.dumps({"error":"invalid_argument_type","field":key})
            output=copy.deepcopy(definition.get("fixture_output") or {"deterministic":True}); output["accepted_arguments"]=args
            output["required_final_facts"]=expected.get("required_final_facts",[])
            next_calls=expected.get("expected_calls",[]); current=next((i for i,x in enumerate(next_calls) if x["name"]==name),None)
            if current is not None and current+1<len(next_calls): output["next_call_arguments"]=next_calls[current+1]["arguments"]
            return json.dumps(output,ensure_ascii=False,separators=(",",":"))
        registry={name:(lambda args,name=name:execute(name,args)) for name in definitions}
        loop=ToolLoopEngine(registry,max_rounds=int(item.get("profile_config",{}).get("max_tool_rounds",3))).run(item.get("messages") or [{"role":"user","content":item["prompt"]}],assistant)
        calls_seen=[]
        for message in loop.get("messages",[]):
            if message.get("role")=="assistant":
                for call in message.get("tool_calls") or []:
                    name,args=_normal_call(call); calls_seen.append({"name":name,"arguments":args})
        timings=[response.get("timing") or {} for response in turn_evidence]
        if timings:
            first_timing, last_timing = timings[0], timings[-1]
            combined_timing = {
                "request_started_at": first_timing.get("request_started_at"),
                "first_chunk_at": next((value.get("first_chunk_at") for value in timings if value.get("first_chunk_at")), None),
                "first_generated_at": next((value.get("first_generated_at") for value in timings if value.get("first_generated_at")), None),
                "first_thinking_at": next((value.get("first_thinking_at") for value in timings if value.get("first_thinking_at")), None),
                "first_final_at": next((value.get("first_final_at") for value in timings if value.get("first_final_at")), None),
                "terminal_record_at": last_timing.get("terminal_record_at"),
                "request_finished_at": last_timing.get("request_finished_at"),
                "client_wall_seconds": sum(float(value.get("client_wall_seconds") or value.get("wall_time_seconds") or 0) for value in timings),
                "time_to_first_chunk_seconds": first_timing.get("time_to_first_chunk_seconds"),
                "time_to_first_generated_seconds": first_timing.get("time_to_first_generated_seconds"),
                "time_to_first_thinking_seconds": first_timing.get("time_to_first_thinking_seconds"),
                "time_to_first_final_seconds": first_timing.get("time_to_first_final_seconds"),
                "practical_within_soft_limit": all(value.get("practical_within_soft_limit", True) for value in timings),
                "turns": timings,
            }
        else:
            stamp = now()
            combined_timing = {"request_started_at":stamp,"first_chunk_at":stamp,"first_generated_at":stamp,"first_thinking_at":None,"first_final_at":stamp,"terminal_record_at":stamp,"request_finished_at":stamp,"client_wall_seconds":0.001,"wall_time_seconds":0.001,"time_to_first_chunk_seconds":0.001,"time_to_first_generated_seconds":0.001,"time_to_first_thinking_seconds":None,"time_to_first_final_seconds":0.001,"practical_within_soft_limit":True}
        return {
            "status":loop["status"], "final_answer":loop.get("final_answer"), "tool_calls":calls_seen,
            "tool_trace":loop.get("messages"),
            "raw_response":turn_evidence if turn_evidence else loop.get("messages"),
            "streamed_chunks":[response.get("streamed_chunks") for response in turn_evidence],
            "thinking":"\n".join(str(response["thinking"]) for response in turn_evidence if response.get("thinking")) or None,
            "ollama_metadata":[response.get("ollama_metadata") or {} for response in turn_evidence],
            "request_payload":{"messages":item.get("messages"),"tools":item.get("tools"),"assistant_turns":[response.get("request_payload") for response in turn_evidence]},
            "timing":combined_timing,
            "terminal_record_seen":all(response.get("terminal_record_seen",False) for response in turn_evidence) if turn_evidence else True,
            "completion_terminal_record":all(response.get("completion_terminal_record",False) for response in turn_evidence) if turn_evidence else True,
            "runtime_anomaly":any(response.get("runtime_anomaly",False) for response in turn_evidence),
            "sampling_policy":item.get("sampling_policy","native_artifact"),
        }


def _run_items(bundle: dict[str, Any], items: list[dict[str, Any]], run_dir: Path, mock: bool, resume_command: str) -> dict[str, Any]:
    run_dir.mkdir(parents=True,exist_ok=True)
    base=MockAdapter() if mock else OllamaAdapter(bundle["config"].get("ollama_api","http://127.0.0.1:11434"),bundle["retry"].get("max_transport_retries",1))
    adapter=RC1Adapter(base,mock)
    breaker_config=bundle["retry"].get("circuit_breaker",{})
    breaker=CircuitBreaker(CircuitConfig(int(breaker_config.get("consecutive_connection_refused_threshold",3)),float(breaker_config.get("healthcheck_wait_seconds",30)),float(breaker_config.get("max_recovery_seconds",900))),lambda: True if mock else healthcheck(bundle["config"].get("ollama_api","http://127.0.0.1:11434")))
    store=EvidenceStore(run_dir); state=store.load_state(); state.update({"benchmark_version":bundle["benchmark"]["benchmark_version"],"task_manifest_hash":bundle["config"]["manifest_hashes"]["task_manifest"],"total_selected_models":len({x["model"] for x in items})}); store.checkpoint(state)
    result=Executor(store,adapter,FormalScorer(bundle),breaker,resume_command=resume_command).run(items)
    if hasattr(adapter, "close"):
        try:
            adapter.close()
        except Exception as exc:
            append_jsonl(store.events, {"event":"model_unload_error","at":now(),"error":f"{type(exc).__name__}: {exc}"})
    completed_models=0
    for model in {x["model"] for x in items}:
        model_items=[x for x in items if x["model"]==model]
        if all(result.get("items",{}).get(logical_key(x),{}).get("inference_status") in TERMINAL_INFERENCE for x in model_items): completed_models+=1
    result.update({"total_selected_models":len({x["model"] for x in items}),"completed_models":completed_models,"current_model":None,"current_task":None,"remaining_task_count":sum(logical_key(x) not in result.get("items",{}) for x in items)})
    store.checkpoint(result)
    return result


def _mock_doctor(config_path: Path) -> tuple[str,list[dict[str,str]]]:
    config=read(config_path); approved=config.get("calibration_approved") is True
    return ("READY" if approved else "NOT_READY", [{"check":"mock_config_parse","status":"PASS","detail":"mock"},{"check":"calibration_approved","status":"PASS" if approved else "FAIL","detail":"mock gate"}])


def _doctor_allows_calibration(result: str, checks: list[dict[str,str]]) -> bool:
    """The initial doctor may fail only the gate that calibration will satisfy."""
    if result == "READY":
        return True
    failed={check.get("check") for check in checks if check.get("status") == "FAIL"}
    return failed == {"calibration_approved"}


def _calibration_entries() -> list[dict[str,Any]]: return read(CONFIG_DIR/"calibration_plan.rc1.json")["entries"]


def _r2_calibration_plan() -> dict[str, Any]: return read(R2_CALIBRATION_PLAN)


def _r3_calibration_plan() -> dict[str, Any]: return read(R3_CALIBRATION_PLAN)


def _inference_saved_counts(run_dir: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    events_path = run_dir / "events.jsonl"
    if not events_path.is_file(): return counts
    with events_path.open(encoding="utf-8") as handle:
        for line in handle:
            try: event = json.loads(line)
            except json.JSONDecodeError: continue
            if event.get("event") == "inference_saved" and event.get("logical_key"):
                key = str(event["logical_key"]); counts[key] = counts.get(key, 0) + 1
    return counts


def _terminal_saved_keys(run_dir: Path) -> set[str]:
    state = EvidenceStore(run_dir).load_state(); keys: set[str] = set()
    for key, entry in (state.get("items") or {}).items():
        raw_path = run_dir / str(entry.get("raw_path")) if entry.get("raw_path") else None
        if entry.get("inference_status") in TERMINAL_INFERENCE and raw_path and raw_path.is_file():
            keys.add(str(key))
    return keys


def _resume_calibration(bundle: dict[str,Any], items: list[dict[str,Any]], run_dir: Path, mock: bool, resume_command: str) -> dict[str, Any]:
    candidate_keys = {logical_key(item) for item in items}
    terminal_keys = _terminal_saved_keys(run_dir) & candidate_keys
    before = _inference_saved_counts(run_dir)
    _run_items(bundle, items, run_dir, mock, resume_command)
    after = _inference_saved_counts(run_dir)
    terminal_stable = bool(terminal_keys) and all(after.get(key, 0) == before.get(key, 0) for key in terminal_keys)
    return {"ok": terminal_stable, "terminal_logical_keys": sorted(terminal_keys), "before": {key: before.get(key, 0) for key in sorted(terminal_keys)}, "after": {key: after.get(key, 0) for key in sorted(terminal_keys)}}


def _raw_evidence(run_dir: Path, state_entry: dict[str, Any]) -> tuple[Path | None, dict[str, Any] | None]:
    path = run_dir / str(state_entry.get("raw_path")) if state_entry.get("raw_path") else None
    return (path, read(path)) if path and path.is_file() else (path, None)


def _score_path(run_dir: Path, raw_path: Path | None) -> Path | None:
    if not raw_path: return None
    return run_dir / "scores" / raw_path.parent.name / raw_path.name


def validate_calibration(run_dir: Path, resume_ok: bool) -> dict[str,Any]:
    state=EvidenceStore(run_dir).load_state(); evidence=[]; score_files=list((run_dir/"scores").rglob("*.json")) if (run_dir/"scores").exists() else []
    for entry in (state.get("items") or {}).values():
        _, value = _raw_evidence(run_dir, entry)
        if value is not None: evidence.append(value)
    gates={
        "runtime_path":bool(evidence),
        "raw_persistence":len(evidence)==len(state.get("items",{})),
        "scorer_path":len(score_files)==len(evidence),
        "thinking_separation":any(x.get("thinking") and x.get("final_answer") and x["thinking"] not in x["final_answer"] for x in evidence),
        "tool_loop":any(x.get("tool_trace") for x in evidence),
        "image_path":any(x.get("images_sent") and (x.get("request_payload",{}).get("messages") or x.get("request_payload",{}).get("images")) for x in evidence),
        "embed_path":any(x.get("corpus_embeddings") and x.get("query_embedding") for x in evidence),
        "safety_parser":any(read(p).get("prediction") is not None for p in score_files),
        "resume":resume_ok,
    }
    result={"schema_version":1,"semantic_correctness_is_not_a_gate":True,"gates":gates,"approved":all(gates.values())}; (run_dir/"calibration_validation.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); return result


def _r2_formal_items(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    allowed = {entry["model"]: set(entry.get("task_ids") or []) for entry in _r2_calibration_plan()["formal_entries"]}
    builder = RC1ItemBuilder(bundle)
    items = [item for item in builder.all_items() if item["model"] in allowed and item["task_id"] in allowed[item["model"]]]
    if any("PERF_01" in task_ids for task_ids in allowed.values()) and (PRIVATE / "tasks" / "PERF_01.json").is_file():
        old_task = read(PRIVATE / "tasks" / "PERF_01.json")
        for model, task_ids in allowed.items():
            if "PERF_01" not in task_ids:
                continue
            model_row = next(row for row in bundle["plan"]["models"] if row["model"] == model)
            base = builder.build(model_row, "PERF_COLD_01")
            base.update({"task_id": "PERF_01", "prompt": old_task.get("prompt", ""), "task_version": old_task.get("version", "1.0-rc1")})
            items.append(base)
    return items


def _build_r2_thinking_probe(bundle: dict[str, Any]) -> dict[str, Any]:
    probe = _r2_calibration_plan()["thinking_probe"]
    metadata = next((row for row in bundle["inventory"]["models"] if row.get("exact_name") == probe["model"]), None)
    capabilities = list((metadata or {}).get("capabilities") or [])
    if "thinking" not in capabilities:
        raise RuntimeError(f"calibration R2 thinking probe model lacks explicit thinking capability: {probe['model']}")
    return {
        "benchmark_version": bundle["benchmark"]["benchmark_version"], "task_manifest_hash": bundle["config"]["manifest_hashes"]["task_manifest"], "scorer_version": bundle["config"]["scorer_version"],
        "model": probe["model"], "exact_model_tag": probe["model"], "model_digest": metadata["digest"], "task_id": probe["task_id"], "track": "calibration_probe", "profile": probe["profile"],
        "profile_config": copy.deepcopy(probe["request_profile"]), "capabilities": capabilities, "prompt": probe["prompt"], "calibration_probe": True,
        "ollama_version": bundle["inventory"].get("ollama_version"), "machine_profile_hash": bundle["config"].get("machine_profile_hash"), "seed_supported": None,
    }


def _run_r2_thinking_probe(bundle: dict[str, Any], item: dict[str, Any], run_dir: Path, mock: bool) -> dict[str, Any]:
    store = EvidenceStore(run_dir); state = store.load_state(); state.update({"benchmark_version": bundle["benchmark"]["benchmark_version"], "task_manifest_hash": bundle["config"]["manifest_hashes"]["task_manifest"]})
    attempt_id = f"probe-{int(time.time() * 1000)}"; store.begin(item, attempt_id)
    adapter = MockAdapter() if mock else OllamaAdapter(bundle["config"].get("ollama_api", "http://127.0.0.1:11434"), bundle["retry"].get("max_transport_retries", 1))
    try: response = adapter.infer(item)
    except Exception as exc: response = {"status": "runner_exception", "error": f"{type(exc).__name__}: {exc}", "finished_at": now()}
    evidence = store.save_inference(item, attempt_id, response); key = logical_key(item)
    state["items"][key] = {"inference_status": evidence["inference_status"], "scoring_status": "probe_only", "raw_path": evidence["raw_path"]}; store.checkpoint(state)
    return evidence


def _r3_formal_items(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    allowed = {entry["model"]: set(entry.get("task_ids") or []) for entry in _r3_calibration_plan()["formal_entries"]}
    items = [item for item in RC1ItemBuilder(bundle).all_items() if item["model"] in allowed and item["task_id"] in allowed[item["model"]]]
    expected = sum(len(task_ids) for task_ids in allowed.values())
    if len(items) != expected:
        raise RuntimeError(f"R3 calibration plan referential mismatch: expected {expected} items, built {len(items)}")
    return items


def _build_r3_thinking_probe(bundle: dict[str, Any]) -> dict[str, Any]:
    probe = _r3_calibration_plan()["thinking_probe"]
    metadata = next((row for row in bundle["inventory"]["models"] if row.get("exact_name") == probe["model"]), None)
    if not metadata:
        raise RuntimeError(f"R3 thinking probe model missing from inventory: {probe['model']}")
    if "thinking" not in set(metadata.get("capabilities") or []):
        raise RuntimeError(f"R3 thinking probe model lacks explicit thinking capability: {probe['model']}")
    runtime_snapshot = next((row for row in bundle.get("runtime_defaults", {}).get("models", []) if row.get("exact_name") == probe["model"]), {})
    return {
        "benchmark_version": bundle["benchmark"]["benchmark_version"],
        "task_manifest_hash": bundle["config"]["manifest_hashes"]["task_manifest"],
        "scorer_version": bundle["config"]["scorer_version"],
        "model": probe["model"], "exact_model_tag": probe["model"], "model_digest": metadata["digest"],
        "task_id": probe["task_id"], "track": "calibration_probe", "profile": probe["profile"],
        "profile_config": copy.deepcopy(probe["request_profile"]), "capabilities": list(metadata.get("capabilities") or []),
        "prompt": probe["prompt"], "calibration_probe": True, "sampling_policy": "native_artifact",
        "runtime_defaults_snapshot_hash": bundle["config"].get("manifest_hashes", {}).get("model_runtime_defaults"),
        "model_modelfile_sha256": runtime_snapshot.get("modelfile_sha256"),
        "reasoning_mode": "requested_thinking", "ollama_version": bundle["inventory"].get("ollama_version"),
        "machine_profile_hash": bundle["config"].get("machine_profile_hash"), "seed_supported": None,
    }


def _run_r3_thinking_probe(bundle: dict[str, Any], item: dict[str, Any], run_dir: Path, mock: bool) -> dict[str, Any]:
    store = EvidenceStore(run_dir)
    state = store.load_state()
    state.update({"benchmark_version": bundle["benchmark"]["benchmark_version"], "task_manifest_hash": bundle["config"]["manifest_hashes"]["task_manifest"]})
    attempt_id = f"probe-{int(time.time() * 1000)}"
    store.begin(item, attempt_id)
    adapter = MockAdapter() if mock else OllamaAdapter(bundle["config"].get("ollama_api", "http://127.0.0.1:11434"), bundle["retry"].get("max_transport_retries", 1))
    try:
        response = adapter.infer(item)
    except Exception as exc:
        response = {"status": "runner_exception", "error": f"{type(exc).__name__}: {exc}", "finished_at": now()}
    evidence = store.save_inference(item, attempt_id, response)
    key = logical_key(item)
    state["items"][key] = {"inference_status": evidence["inference_status"], "scoring_status": "probe_only", "raw_path": evidence["raw_path"], "terminal_record_seen": evidence.get("terminal_record_seen"), "runtime_anomaly": evidence.get("runtime_anomaly")}
    store.checkpoint(state)
    return evidence


def validate_calibration_r2(run_dir: Path, formal_items: list[dict[str, Any]], probe_item: dict[str, Any], resume_result: dict[str, Any]) -> dict[str, Any]:
    state = EvidenceStore(run_dir).load_state(); state_items = state.get("items") or {}; formal_keys = {logical_key(item) for item in formal_items}; probe_key = logical_key(probe_item)
    formal_evidence: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []; raw_ok = True; score_ok = True; guardian_requests_ok = True; guardian_predictions_ok = True; performance_status = None; scoring_error_keys: set[str] = set()
    events_path = run_dir / "events.jsonl"
    if events_path.is_file():
        with events_path.open(encoding="utf-8") as handle:
            for line in handle:
                try: event = json.loads(line)
                except json.JSONDecodeError: continue
                if event.get("event") == "scoring_error" and event.get("logical_key") in formal_keys: scoring_error_keys.add(str(event["logical_key"]))
    for item in formal_items:
        key = logical_key(item); entry = state_items.get(key) or {}; raw_path, evidence = _raw_evidence(run_dir, entry); raw_ok = raw_ok and evidence is not None
        score_path = _score_path(run_dir, raw_path); score = read(score_path) if score_path and score_path.is_file() else None; score_ok = score_ok and score is not None and entry.get("scoring_status") != "scoring_error" and key not in scoring_error_keys
        if evidence is not None and score is not None: formal_evidence.append((item, evidence, score))
        if item["model"] == "granite4.1-guardian:8b" and item["track"] == "safety":
            guardian_requests_ok = guardian_requests_ok and (evidence or {}).get("request_payload", {}).get("think") is False
            guardian_predictions_ok = guardian_predictions_ok and score is not None and score.get("prediction") is not None
        if item["task_id"] == "PERF_01": performance_status = (evidence or {}).get("inference_status")
    probe_entry = state_items.get(probe_key) or {}; probe_raw_path, persisted_probe = _raw_evidence(run_dir, probe_entry); raw_ok = raw_ok and persisted_probe is not None
    probe = persisted_probe or {}
    probe_request = probe.get("request_payload") or {}
    thinking_ok = probe_request.get("think") is True and isinstance(probe.get("thinking"), str) and bool(probe.get("thinking")) and isinstance(probe.get("final_answer"), str) and bool(probe.get("final_answer")) and probe["thinking"] not in probe["final_answer"]
    gates = {
        "scorer_path": bool(formal_items) and score_ok,
        "thinking_separation": thinking_ok,
        "resume_dedup": bool(resume_result.get("ok")),
        "tool_loop": any(evidence.get("tool_trace") for _, evidence, _ in formal_evidence),
        "image_path": any(evidence.get("images_sent") and ((evidence.get("request_payload") or {}).get("messages") or (evidence.get("request_payload") or {}).get("images")) for _, evidence, _ in formal_evidence),
        "embed_path": any(evidence.get("corpus_embeddings") and evidence.get("query_embedding") for _, evidence, _ in formal_evidence),
        "safety_parser": guardian_requests_ok and guardian_predictions_ok,
        "performance_path": performance_status == "completed",
        "raw_persistence": raw_ok and set(state_items).issuperset(formal_keys | {probe_key}),
    }
    result = {"schema_version": 2, "benchmark_version": "1.0-rc1", "calibration": "R2", "semantic_correctness_is_not_a_gate": True, "gates": gates, "approved": all(gates.values()), "details": {"guardian_think_false": guardian_requests_ok, "guardian_prediction_present": guardian_predictions_ok, "performance_status": performance_status, "probe_task_id": probe_item["task_id"], "resume": resume_result}}
    (run_dir / "calibration_r2_validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def _iso_after(first: str | None, second: str | None) -> bool:
    if not first or not second:
        return False
    try:
        return dt.datetime.fromisoformat(first) >= dt.datetime.fromisoformat(second)
    except (TypeError, ValueError):
        return False


def validate_calibration_r3(run_dir: Path, formal_items: list[dict[str, Any]], probe_item: dict[str, Any], resume_result: dict[str, Any]) -> dict[str, Any]:
    state = EvidenceStore(run_dir).load_state()
    state_items = state.get("items") or {}
    formal_keys = {logical_key(item) for item in formal_items}
    probe_key = logical_key(probe_item)
    records: dict[str, tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]] = {}
    scoring_errors: set[str] = set()
    events_path = run_dir / "events.jsonl"
    if events_path.is_file():
        with events_path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if event.get("event") == "scoring_error" and event.get("logical_key") in formal_keys:
                    scoring_errors.add(str(event["logical_key"]))
    for item in formal_items + [probe_item]:
        key = logical_key(item)
        entry = state_items.get(key) or {}
        raw_path, evidence = _raw_evidence(run_dir, entry)
        score_path = _score_path(run_dir, raw_path)
        score = read(score_path) if score_path and score_path.is_file() else None
        records[key] = (item, evidence, score)

    formal_records = [records[logical_key(item)] for item in formal_items]
    probe = records[probe_key][1] or {}
    probe_request = probe.get("request_payload") or {}
    selected_native = [record for record in formal_records if record[0]["model"] in {"qwen3.5:4b", "nemotron-3-nano:4b", "phi4-mini:latest"}]
    forbidden_sampling = {"temperature", "top_k", "top_p", "min_p", "typical_p", "repeat_penalty", "presence_penalty", "frequency_penalty", "seed"}
    native_ok = bool(selected_native) and all(not (set(((record[1] or {}).get("request_payload") or {}).get("options", {})) & forbidden_sampling) for record in selected_native)
    thinking_ok = (
        probe.get("inference_status") == "completed"
        and probe_request.get("think") is True
        and isinstance(probe.get("thinking"), str) and bool(probe.get("thinking"))
        and isinstance(probe.get("final_answer"), str) and bool(probe.get("final_answer"))
        and probe["thinking"] != probe["final_answer"]
        and probe.get("terminal_record_seen") is True
        and probe.get("completion_terminal_record") is True
    )
    required_timing = {"request_started_at", "first_chunk_at", "first_generated_at", "first_thinking_at", "first_final_at", "terminal_record_at", "request_finished_at", "client_wall_seconds", "time_to_first_chunk_seconds", "time_to_first_generated_seconds", "time_to_first_thinking_seconds", "time_to_first_final_seconds"}
    timing_ok = all(required_timing.issubset(set((evidence or {}).get("timing", {}))) for _, evidence, _ in formal_records)
    preload_ok = True
    preload_details = {}
    for model in {"qwen3.5:4b", "nemotron-3-nano:4b"}:
        record = next((record for record in formal_records if record[0]["model"] == model and (record[1] or {}).get("preload")), None)
        preload = (record[1] or {}).get("preload") if record else None
        good = bool(record and preload and preload.get("status") == "completed" and preload.get("request_payload") == {"model": model, "keep_alive": "5m"} and _iso_after((record[1] or {}).get("timing", {}).get("request_started_at"), preload.get("request_finished_at")))
        preload_details[model] = good
        preload_ok = preload_ok and good
    performance = {(record[0]["model"], record[0]["task_id"]): record[1] or {} for record in formal_records if record[0]["task_id"] in {"PERF_COLD_01", "PERF_WARM_01"}}
    performance_ok = len(performance) == 4
    for evidence in performance.values():
        chunks = evidence.get("streamed_chunks") or []
        metadata = evidence.get("ollama_metadata") or {}
        performance_ok = performance_ok and evidence.get("inference_status") == "completed" and evidence.get("terminal_record_seen") is True and bool(chunks) and chunks[-1].get("done") is True and all(key in metadata for key in ("eval_count", "eval_duration", "total_duration"))
    warm_eval_counts = [int((evidence.get("ollama_metadata") or {}).get("eval_count")) for (model, task), evidence in performance.items() if task == "PERF_WARM_01" and (evidence.get("ollama_metadata") or {}).get("eval_count") is not None]
    performance_comparable = any(count >= 128 for count in warm_eval_counts)
    scores_present = all(score is not None and key not in scoring_errors for key, (_, evidence, score) in records.items() if key in formal_keys and evidence is not None and evidence.get("inference_status") not in INFRA_FAILURE)
    tool_ok = any((evidence or {}).get("tool_trace") or (evidence or {}).get("tool_calls") for item, evidence, _ in formal_records if item["track"] == "tools")
    image_ok = any((evidence or {}).get("images_sent") and (((evidence or {}).get("request_payload") or {}).get("messages") or ((evidence or {}).get("request_payload") or {}).get("images")) for item, evidence, _ in formal_records if item["track"] == "vision")
    embed_ok = any((evidence or {}).get("corpus_embeddings") and (evidence or {}).get("query_embedding") for item, evidence, _ in formal_records if item["track"] == "embedding")
    safety_ok = True
    for item, evidence, score in formal_records:
        if item["track"] == "safety":
            safety_ok = safety_ok and score is not None and score.get("prediction") is not None and (item["model"] != "granite4.1-guardian:8b" or (evidence or {}).get("request_payload", {}).get("think") is False)
    raw_ok = all(records[key][1] is not None for key in formal_keys | {probe_key})
    hash_ok = all(
        evidence is not None
        and evidence.get("task_manifest_hash") == item.get("task_manifest_hash")
        and evidence.get("model_digest") == item.get("model_digest")
        and evidence.get("sampling_policy") in {"native_artifact", "architect_model_override", "benchmark_standardized"}
        and evidence.get("evidence_payload_sha256")
        for item, evidence, _ in formal_records + [(probe_item, probe, None)]
    )
    gates = {
        "native_sampling_request": native_ok,
        "thinking_separation": thinking_ok,
        "preload_path": preload_ok,
        "timing_fields": timing_ok,
        "performance_cold_warm": performance_ok,
        "performance_comparability_probe": performance_comparable,
        "tool_loop": tool_ok,
        "image_path": image_ok,
        "embed_path": embed_ok,
        "safety_parser": safety_ok,
        "scorer_path": bool(formal_records) and scores_present,
        "resume_dedup": bool(resume_result.get("ok")),
        "raw_persistence": raw_ok,
        "hash_integrity": hash_ok,
    }
    result = {
        "schema_version": 3,
        "benchmark_version": "1.0-rc1",
        "calibration": "R3",
        "semantic_correctness_is_not_a_gate": True,
        "gates": gates,
        "approved": all(gates.values()),
        "details": {
            "formal_item_count": len(formal_items),
            "performance_records": len(performance),
            "performance_warm_eval_counts": warm_eval_counts,
            "preload_models": preload_details,
            "thinking_probe_task_id": probe_item["task_id"],
            "thinking_probe_has_text": bool(probe.get("thinking")) and bool(probe.get("final_answer")),
            "resume": resume_result,
            "scoring_error_count": len(scoring_errors),
        },
    }
    (run_dir / "calibration_r3_validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def calibrate(bundle: dict[str,Any], args: argparse.Namespace) -> int:
    if not args.mock:
        if not args.allow_inference:
            print(json.dumps({"status":"NOT_RUN","reason":"calibration requires --allow-inference and explicit approved configuration","plan":str(CONFIG_DIR/"calibration_plan.rc1.json")},ensure_ascii=False,indent=2)); return 2
        allowed={x["model"]:set(x["task_ids"]) for x in _calibration_entries()}; items=[x for x in RC1ItemBuilder(bundle).all_items() if x["model"] in allowed and x["task_id"] in allowed[x["model"]]]
        run_dir=Path(args.run_dir) if args.run_dir else DEFAULT_RUN_ROOT/"calibration"
        _run_items(bundle,items,run_dir,False,f"python scripts/rc1_runner.py calibrate --allow-inference --run-dir {run_dir}"); resume_result=_resume_calibration(bundle,items,run_dir,False,f"python scripts/rc1_runner.py calibrate --allow-inference --run-dir {run_dir}"); validation=validate_calibration(run_dir,resume_result["ok"])
        print(json.dumps({"status":"COMPLETED" if validation["approved"] else "FAILED","items":len(items),"run_dir":str(run_dir),"gates":validation["gates"],"resume":resume_result},ensure_ascii=False,indent=2)); return 0 if validation["approved"] else 2
    allowed={x["model"]:set(x["task_ids"]) for x in _calibration_entries()}; items=[x for x in RC1ItemBuilder(bundle).all_items() if x["model"] in allowed and x["task_id"] in allowed[x["model"]]]
    run_dir=Path(args.run_dir) if args.run_dir else DEFAULT_RUN_ROOT/"mock_calibration"
    _run_items(bundle,items,run_dir,True,f"python scripts/rc1_runner.py calibrate --mock --run-dir {run_dir}"); resume_result=_resume_calibration(bundle,items,run_dir,True,f"python scripts/rc1_runner.py calibrate --mock --run-dir {run_dir}"); validation=validate_calibration(run_dir,resume_result["ok"])
    print(json.dumps({"status":"MOCK_COMPLETED" if validation["approved"] else "MOCK_FAILED","items":len(items),"run_dir":str(run_dir),"gates":validation["gates"],"resume":resume_result},ensure_ascii=False,indent=2)); return 0 if validation["approved"] else 2


def calibrate_r2(bundle: dict[str, Any], args: argparse.Namespace) -> int:
    if not args.mock and not args.allow_inference:
        print(json.dumps({"status": "NOT_RUN", "reason": "calibration R2 requires --allow-inference", "plan": str(R2_CALIBRATION_PLAN)}, ensure_ascii=False, indent=2)); return 2
    formal_items = _r2_formal_items(bundle); probe_item = _build_r2_thinking_probe(bundle); run_dir = Path(args.run_dir) if args.run_dir else DEFAULT_RUN_ROOT / "calibration_r2"
    _run_items(bundle, formal_items, run_dir, args.mock, f"python scripts/rc1_runner.py calibrate-r2 {'--mock ' if args.mock else '--allow-inference '}--run-dir {run_dir}")
    probe_evidence = _run_r2_thinking_probe(bundle, probe_item, run_dir, args.mock)
    resume_result = _resume_calibration(bundle, formal_items, run_dir, args.mock, f"python scripts/rc1_runner.py calibrate-r2 {'--mock ' if args.mock else '--allow-inference '}--run-dir {run_dir}")
    validation = validate_calibration_r2(run_dir, formal_items, probe_item, resume_result)
    status = "CALIBRATION_R2_PASS" if validation["approved"] else "CALIBRATION_R2_BLOCKED"
    print(json.dumps({"status": status, "formal_items": len(formal_items), "probe_task_id": probe_item["task_id"], "run_dir": str(run_dir), "gates": validation["gates"], "resume": resume_result}, ensure_ascii=False, indent=2))
    return 0 if validation["approved"] else 2


def calibrate_r3(bundle: dict[str, Any], args: argparse.Namespace) -> int:
    if not args.mock and not args.allow_inference:
        print(json.dumps({"status": "NOT_RUN", "reason": "calibration R3 requires --allow-inference", "plan": str(R3_CALIBRATION_PLAN)}, ensure_ascii=False, indent=2))
        return 2
    formal_items = _r3_formal_items(bundle)
    probe_item = _build_r3_thinking_probe(bundle)
    run_dir = Path(args.run_dir) if args.run_dir else DEFAULT_RUN_ROOT / "calibration_r3"
    resume_command = f"python scripts/rc1_runner.py calibrate-r3 {'--mock ' if args.mock else '--allow-inference '}--run-dir {run_dir}"
    _run_items(bundle, formal_items, run_dir, args.mock, resume_command)
    _run_r3_thinking_probe(bundle, probe_item, run_dir, args.mock)
    resume_result = _resume_calibration(bundle, formal_items, run_dir, args.mock, resume_command)
    validation = validate_calibration_r3(run_dir, formal_items, probe_item, resume_result)
    status = "CALIBRATION_R3_PASS" if validation["approved"] else "CALIBRATION_R3_BLOCKED"
    print(json.dumps({"status": status, "formal_items": len(formal_items), "probe_task_id": probe_item["task_id"], "run_dir": str(run_dir), "gates": validation["gates"], "resume": resume_result}, ensure_ascii=False, indent=2))
    return 0 if validation["approved"] else 2


def run_all(bundle: dict[str,Any], args: argparse.Namespace) -> int:
    run_dir=Path(args.run_dir) if args.run_dir else DEFAULT_RUN_ROOT/"rc1_run"
    if not args.mock:
        result,checks=luna_doctor(Path(args.config)); print(json.dumps({"result":result,"checks":checks},ensure_ascii=False,indent=2))
        if result!="READY": print("RUN_REFUSED: doctor must be READY"); return 2
        if not args.allow_inference: print("RUN_REFUSED: --allow-inference is required for real inference"); return 2
    items=RC1ItemBuilder(bundle).all_items(args.model,args.task)
    state=_run_items(bundle,items,run_dir,args.mock,f"python scripts/rc1_runner.py resume {'--mock ' if args.mock else ''}--run-dir {run_dir}")
    print(json.dumps({"status":"MOCK_COMPLETED" if args.mock else "COMPLETED","items":len(items),"state_items":len(state.get("items",{})),"run_dir":str(run_dir)},ensure_ascii=False,indent=2)); return 0


def status_command(args: argparse.Namespace) -> int:
    path=Path(args.run_dir) if args.run_dir else DEFAULT_RUN_ROOT/"rc1_run"; print(json.dumps(luna_status(path),ensure_ascii=False,indent=2)); return 0


def finalize_command(args: argparse.Namespace) -> int:
    run_dir=Path(args.run_dir); output=Path(args.output) if args.output else ROOT/"public_results"/(run_dir.name+".jsonl"); output.parent.mkdir(parents=True,exist_ok=True); state=EvidenceStore(run_dir).load_state(); rows=[]
    for key,entry in state.get("items",{}).items():
        raw_path=run_dir/str(entry.get("raw_path")) if entry.get("raw_path") else None
        raw=read(raw_path) if raw_path and raw_path.is_file() else {}
        score_path=None
        if raw_path: score_path=run_dir/"scores"/raw_path.parent.name/Path(raw_path.name).name
        row={"logical_key":key,"model":raw.get("model"),"model_digest":raw.get("model_digest"),"task_id":raw.get("task_id"),"profile":raw.get("profile"),"inference_status":raw.get("inference_status"),"scoring_status":entry.get("scoring_status"),"timing":raw.get("timing",{})}
        if score_path and score_path.is_file(): row["score"]=read(score_path).get("score")
        rows.append(row)
    with output.open("w",encoding="utf-8",newline="\n") as handle:
        for row in rows: handle.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")
    print(json.dumps({"status":"FINALIZED","rows":len(rows),"output":str(output)},ensure_ascii=False,indent=2)); return 0


def launch(bundle: dict[str,Any], args: argparse.Namespace) -> int:
    if not args.mock:
        if not args.allow_inference:
            print("LAUNCH_REFUSED: --allow-inference is required; no calibration or formal inference is started")
            return 2
        result,checks=luna_doctor(Path(args.config)); print(json.dumps({"stage":"doctor","result":result,"checks":checks},ensure_ascii=False,indent=2))
        if not _doctor_allows_calibration(result,checks): print("LAUNCH_STOP: pre-calibration doctor has blocking failures"); return 2
        calibration_args=argparse.Namespace(**vars(args)); calibration_args.mock=False; calibration_args.run_dir=str(DEFAULT_RUN_ROOT/"calibration");
        if calibrate(bundle,calibration_args)!=0: print("LAUNCH_STOP: calibration validation failed"); return 2
        approved=DEFAULT_RUN_ROOT/"approved_run_config.json"; config=copy.deepcopy(bundle["config"]); config["calibration_approved"]=True; approved.parent.mkdir(parents=True,exist_ok=True); approved.write_text(json.dumps(config,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        approved_result,_=luna_doctor(approved)
        if approved_result!="READY": print("LAUNCH_STOP: approved doctor must be READY"); return 2
        run_args=argparse.Namespace(**vars(args)); run_args.config=str(approved); run_args.mock=False; run_args.run_dir=str(DEFAULT_RUN_ROOT/"rc1_run")
        if run_all(bundle,run_args)!=0: return 2
        return finalize_command(argparse.Namespace(run_dir=str(DEFAULT_RUN_ROOT/"rc1_run"),output=str(ROOT/"public_results"/"rc1_run.jsonl")))
    root=Path(args.run_dir) if args.run_dir else Path(tempfile.mkdtemp(prefix="rc1-launch-mock-")); root.mkdir(parents=True,exist_ok=True)
    initial_result,initial_checks=_mock_doctor(Path(args.config))
    if not _doctor_allows_calibration(initial_result,initial_checks): print("MOCK_LAUNCH_STOP: pre-calibration doctor failed"); return 2
    calibration_args=argparse.Namespace(**vars(args)); calibration_args.mock=True; calibration_args.run_dir=str(root/"calibration")
    if calibrate(bundle,calibration_args)!=0: print("MOCK_LAUNCH_STOP: calibration validation failed"); return 2
    approved=root/"approved_run_config.json"; config=copy.deepcopy(bundle["config"]); config["calibration_approved"]=True; approved.write_text(json.dumps(config,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    doctor_result,_=_mock_doctor(approved)
    if doctor_result!="READY": print("MOCK_LAUNCH_STOP: approved doctor failed"); return 2
    all_items=RC1ItemBuilder(bundle).all_items(); selected=[]; tracks=set()
    for item in all_items:
        if item["track"] not in tracks: selected.append(item); tracks.add(item["track"])
    run_args=argparse.Namespace(**vars(args)); run_args.run_dir=str(root/"run"); run_args.mock=True
    _run_items(bundle,selected,Path(run_args.run_dir),True,f"python scripts/rc1_runner.py resume --mock --run-dir {run_args.run_dir}")
    finalize_command(argparse.Namespace(run_dir=str(root/"run"),output=str(root/"public_results.jsonl")))
    print(json.dumps({"status":"MOCK_LAUNCH_COMPLETED","doctor":"READY","calibration":"MOCK_COMPLETED","run_dir":str(root/"run")},ensure_ascii=False,indent=2)); return 0


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description="SummerTestModel RC1 formal execution wiring")
    parser.add_argument("command",choices=["doctor","calibrate","calibrate-r2","calibrate-r3","run-all","resume","status","finalize","launch"])
    parser.add_argument("--config",default=str(DEFAULT_CONFIG)); parser.add_argument("--run-dir"); parser.add_argument("--output"); parser.add_argument("--model"); parser.add_argument("--task"); parser.add_argument("--mock",action="store_true"); parser.add_argument("--allow-inference",action="store_true")
    args=parser.parse_args(argv); bundle=config_bundle(Path(args.config))
    if args.command=="doctor":
        if args.mock: result,checks=_mock_doctor(Path(args.config))
        else: result,checks=luna_doctor(Path(args.config))
        print(json.dumps({"result":result,"checks":checks},ensure_ascii=False,indent=2)); return 0 if result=="READY" else 1
    if args.command=="calibrate": return calibrate(bundle,args)
    if args.command=="calibrate-r2": return calibrate_r2(bundle,args)
    if args.command=="calibrate-r3": return calibrate_r3(bundle,args)
    if args.command in {"run-all","resume"}: return run_all(bundle,args)
    if args.command=="status": return status_command(args)
    if args.command=="finalize": return finalize_command(args)
    return launch(bundle,args)


if __name__=="__main__": raise SystemExit(main())
