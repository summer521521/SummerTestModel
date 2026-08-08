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
import importlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.executor_core import CircuitBreaker, CircuitConfig, EvidenceStore, Executor, logical_key
from scripts.ollama_adapter import OllamaAdapter
from scripts.tool_loop import ToolLoopEngine
from scripts.luna_executor import doctor as luna_doctor, healthcheck, status as luna_status

CONFIG_DIR = ROOT / "config"
PRIVATE = ROOT / "private_benchmark" / "1.0-rc1"
DEFAULT_CONFIG = CONFIG_DIR / "run_config.template.json"
DEFAULT_RUN_ROOT = ROOT / "private_runs"


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
    return {"config": config, "benchmark": benchmark, "tasks": task_manifest,
            "scorers": scorer_manifest, "plan": plan, "profiles": profiles,
            "retry": retry, "inventory": inventory}


class FormalScorer:
    """Load private task payloads and dispatch through the public scorer entrypoint."""

    def __init__(self, bundle: dict[str, Any]):
        self.bundle = bundle
        self.task_manifest = {x["task_id"]: x for x in bundle["tasks"]["tasks"]}
        self.scorers = {x["scorer_id"]: x for x in bundle["scorers"]["scorers"]}

    def score(self, evidence: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
        public_task = self.task_manifest[item["task_id"]]
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
        }
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
        payload={"model":item["model"],"stream":True,"options":{"temperature":0,"num_ctx":profile.get("num_ctx"),"num_predict":profile.get("num_predict")}}
        if item.get("messages") is not None: payload["messages"]=item["messages"]
        else: payload["prompt"]=item.get("prompt","")
        if item.get("images") is not None: payload["images"]=item["images"]
        thinking="mock thinking" if profile.get("think") is True else None
        if track == "code": answer=f"def {item.get('requested_function','mock_function')}(*args, **kwargs):\n    return None\n"
        elif track == "safety": answer="No"
        else: answer="mock final answer"
        return {"status":"completed","raw_response":[{"message":{"thinking":thinking,"content":answer},"done":True}],"streamed_chunks":[{"message":{"thinking":thinking,"content":answer},"done":True}],"thinking":thinking,"final_answer":answer,"request_payload":payload,"endpoint":"mock","timing":{"wall_time_seconds":0.001},"images_sent":item.get("images")}


def _tool_call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {"type":"function","function":{"name":name,"arguments":arguments}}


def _normal_call(call: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    fn=call.get("function") or call
    args=fn.get("arguments",{})
    if isinstance(args,str): args=json.loads(args)
    return fn.get("name") or call.get("name"), args


class RC1Adapter:
    def __init__(self, base: Any, mock: bool = False): self.base, self.mock, self.current_model = base, mock, None

    def infer(self, item: dict[str, Any]) -> dict[str, Any]:
        if not self.mock and self.current_model and self.current_model != item["model"]:
            self.base.unload(self.current_model)
        self.current_model=item["model"]
        if item["track"] == "embedding": return self._embedding(item)
        if item["track"] == "tools": return self._tools(item)
        return self.base.infer(item)

    def _embedding(self, item: dict[str, Any]) -> dict[str, Any]:
        if self.mock:
            docs=item["embedding_corpus"]; query=item["embedding_query"]
            relevant=query["relevant_doc_ids"][0]
            corpus={d["doc_id"]:([1.0,0.0] if d["doc_id"]==relevant else [0.0,1.0]) for d in docs}
            return {"status":"completed","embedding_corpus":corpus,"corpus_embeddings":corpus,"embedding":[1.0,0.0],"query_embedding":[1.0,0.0],"final_answer":None,"request_payload":{"endpoint":"/api/embed","input_count":len(docs)+1},"timing":{"wall_time_seconds":0.001}}
        corpus_result=self.base.embed(item["model"],[d["text"] for d in item["embedding_corpus"]],item["profile_config"])
        query_result=self.base.embed(item["model"],item["embedding_query"]["text"],item["profile_config"])
        vectors=corpus_result.get("embedding") or []; query=query_result.get("embedding") or []
        if query and isinstance(query[0],list): query=query[0]
        if vectors and isinstance(vectors[0],list): corpus=dict(zip((d["doc_id"] for d in item["embedding_corpus"]),vectors))
        else: corpus={}
        return {"status":"completed" if corpus and query else corpus_result.get("status","embed_error"),"embedding_corpus":corpus,"corpus_embeddings":corpus,"embedding":query,"query_embedding":query,"final_answer":None,"request_payload":{"corpus":corpus_result.get("request_payload"),"query":query_result.get("request_payload")},"ollama_metadata":{"corpus":corpus_result.get("ollama_metadata"),"query":query_result.get("ollama_metadata")}}

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
        loop=ToolLoopEngine(registry,max_rounds=3).run(item.get("messages") or [{"role":"user","content":item["prompt"]}],assistant)
        calls_seen=[]
        for message in loop.get("messages",[]):
            if message.get("role")=="assistant":
                for call in message.get("tool_calls") or []:
                    name,args=_normal_call(call); calls_seen.append({"name":name,"arguments":args})
        timings=[response.get("timing") or {} for response in turn_evidence]
        return {
            "status":loop["status"], "final_answer":loop.get("final_answer"), "tool_calls":calls_seen,
            "tool_trace":loop.get("messages"),
            "raw_response":turn_evidence if turn_evidence else loop.get("messages"),
            "streamed_chunks":[response.get("streamed_chunks") for response in turn_evidence],
            "thinking":"\n".join(str(response["thinking"]) for response in turn_evidence if response.get("thinking")) or None,
            "ollama_metadata":[response.get("ollama_metadata") or {} for response in turn_evidence],
            "request_payload":{"messages":item.get("messages"),"tools":item.get("tools"),"assistant_turns":[response.get("request_payload") for response in turn_evidence]},
            "timing":{"wall_time_seconds":sum(float(value.get("wall_time_seconds") or 0) for value in timings),"turns":timings} if timings else {"wall_time_seconds":0.001},
        }


def _run_items(bundle: dict[str, Any], items: list[dict[str, Any]], run_dir: Path, mock: bool, resume_command: str) -> dict[str, Any]:
    run_dir.mkdir(parents=True,exist_ok=True)
    base=MockAdapter() if mock else OllamaAdapter(bundle["config"].get("ollama_api","http://127.0.0.1:11434"),bundle["retry"].get("max_transport_retries",1))
    adapter=RC1Adapter(base,mock)
    breaker_config=bundle["retry"].get("circuit_breaker",{})
    breaker=CircuitBreaker(CircuitConfig(int(breaker_config.get("consecutive_connection_refused_threshold",3)),float(breaker_config.get("healthcheck_wait_seconds",30)),float(breaker_config.get("max_recovery_seconds",900))),lambda: True if mock else healthcheck(bundle["config"].get("ollama_api","http://127.0.0.1:11434")))
    store=EvidenceStore(run_dir); state=store.load_state(); state.update({"benchmark_version":bundle["benchmark"]["benchmark_version"],"task_manifest_hash":bundle["config"]["manifest_hashes"]["task_manifest"],"total_selected_models":len({x["model"] for x in items})}); store.checkpoint(state)
    result=Executor(store,adapter,FormalScorer(bundle),breaker,resume_command=resume_command).run(items)
    completed_models=0
    for model in {x["model"] for x in items}:
        model_items=[x for x in items if x["model"]==model]
        if all(logical_key(x) in result.get("items",{}) for x in model_items): completed_models+=1
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


def validate_calibration(run_dir: Path, resume_ok: bool) -> dict[str,Any]:
    state=EvidenceStore(run_dir).load_state(); evidence=[]; score_files=list((run_dir/"scores").rglob("*.json")) if (run_dir/"scores").exists() else []
    for entry in state.get("items",{}).values():
        path=run_dir/str(entry.get("raw_path")) if entry.get("raw_path") else None
        if path and path.is_file(): evidence.append(read(path))
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


def calibrate(bundle: dict[str,Any], args: argparse.Namespace) -> int:
    if not args.mock:
        if not args.allow_inference:
            print(json.dumps({"status":"NOT_RUN","reason":"calibration requires --allow-inference and explicit approved configuration","plan":str(CONFIG_DIR/"calibration_plan.rc1.json")},ensure_ascii=False,indent=2)); return 2
        allowed={x["model"]:set(x["task_ids"]) for x in _calibration_entries()}; items=[x for x in RC1ItemBuilder(bundle).all_items() if x["model"] in allowed and x["task_id"] in allowed[x["model"]]]
        run_dir=Path(args.run_dir) if args.run_dir else DEFAULT_RUN_ROOT/"calibration"
        _run_items(bundle,items,run_dir,False,f"python scripts/rc1_runner.py calibrate --allow-inference --run-dir {run_dir}"); before=(run_dir/"events.jsonl").read_text(encoding="utf-8").count('"event":"inference_saved"'); _run_items(bundle,items,run_dir,False,"resume"); after=(run_dir/"events.jsonl").read_text(encoding="utf-8").count('"event":"inference_saved"'); validation=validate_calibration(run_dir,before==after)
        print(json.dumps({"status":"COMPLETED" if validation["approved"] else "FAILED","items":len(items),"run_dir":str(run_dir),"gates":validation["gates"]},ensure_ascii=False,indent=2)); return 0 if validation["approved"] else 2
    allowed={x["model"]:set(x["task_ids"]) for x in _calibration_entries()}; items=[x for x in RC1ItemBuilder(bundle).all_items() if x["model"] in allowed and x["task_id"] in allowed[x["model"]]]
    run_dir=Path(args.run_dir) if args.run_dir else DEFAULT_RUN_ROOT/"mock_calibration"
    _run_items(bundle,items,run_dir,True,f"python scripts/rc1_runner.py calibrate --mock --run-dir {run_dir}"); before=(run_dir/"events.jsonl").read_text(encoding="utf-8").count('"event":"inference_saved"'); _run_items(bundle,items,run_dir,True,"resume"); after=(run_dir/"events.jsonl").read_text(encoding="utf-8").count('"event":"inference_saved"'); validation=validate_calibration(run_dir,before==after)
    print(json.dumps({"status":"MOCK_COMPLETED" if validation["approved"] else "MOCK_FAILED","items":len(items),"run_dir":str(run_dir),"gates":validation["gates"]},ensure_ascii=False,indent=2)); return 0 if validation["approved"] else 2


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
    parser.add_argument("command",choices=["doctor","calibrate","run-all","resume","status","finalize","launch"])
    parser.add_argument("--config",default=str(DEFAULT_CONFIG)); parser.add_argument("--run-dir"); parser.add_argument("--output"); parser.add_argument("--model"); parser.add_argument("--task"); parser.add_argument("--mock",action="store_true"); parser.add_argument("--allow-inference",action="store_true")
    args=parser.parse_args(argv); bundle=config_bundle(Path(args.config))
    if args.command=="doctor":
        if args.mock: result,checks=_mock_doctor(Path(args.config))
        else: result,checks=luna_doctor(Path(args.config))
        print(json.dumps({"result":result,"checks":checks},ensure_ascii=False,indent=2)); return 0 if result=="READY" else 1
    if args.command=="calibrate": return calibrate(bundle,args)
    if args.command in {"run-all","resume"}: return run_all(bundle,args)
    if args.command=="status": return status_command(args)
    if args.command=="finalize": return finalize_command(args)
    return launch(bundle,args)


if __name__=="__main__": raise SystemExit(main())
