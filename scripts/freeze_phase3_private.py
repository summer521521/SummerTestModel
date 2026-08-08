"""Freeze Phase 3 metadata and private payload from the architect attachment.

The source path is an input artifact outside Git. This script writes only the
ignored private package plus public ID/hash manifests and assignment metadata.
It never writes exact prompts or answers to tracked files.
"""
from __future__ import annotations
import hashlib, json, re, shutil, sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "private_benchmark" / "1.0-rc1"
CORE = "deepscaler:1.5b|deepseek-r1:8b|gemma3n:e4b|gemma4:e4b|granite4.1:8b|granite4:7b-a1b-h|hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M|hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M|hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M|hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL|huggingface.co/llmware/phi-4-mini-gguf:latest|huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest|lfm2.5:8b|llama3.2:3b|minicpm-v4.6:latest|ministral-3:8b|mistral:7b|nemotron-3-nano:4b|olmo-3:7b-instruct|olmo-3:7b-think|openbmb/minicpm5:Q4_K_M|ornith:9b|phi4-mini-reasoning:latest|phi4-mini:latest|qwen3-vl:8b|qwen3.5:4b|qwen3.5:9b|rnj-1:latest|smollm2:1.7b".split("|")
REASONING = "deepscaler:1.5b|deepseek-r1:8b|gemma4:e4b|hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M|hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M|hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL|huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest|lfm2.5:8b|minicpm-v4.6:latest|nemotron-3-nano:4b|olmo-3:7b-think|openbmb/minicpm5:Q4_K_M|ornith:9b|qwen3-vl:8b|qwen3.5:4b|qwen3.5:9b|phi4-mini-reasoning:latest".split("|")
TOOLS = "functiongemma:270m|deepscaler:1.5b|deepseek-r1:8b|gemma4:e4b|granite4.1:8b|granite4:7b-a1b-h|hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M|hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M|hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M|hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL|huggingface.co/llmware/phi-4-mini-gguf:latest|huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest|lfm2.5:8b|llama3.2:3b|minicpm-v4.6:latest|ministral-3:8b|mistral:7b|nemotron-3-nano:4b|olmo-3:7b-instruct|openbmb/minicpm5:Q4_K_M|ornith:9b|phi4-mini-reasoning:latest|phi4-mini:latest|qwen3-vl:8b|qwen3.5:4b|qwen3.5:9b|rnj-1:latest|smollm2:1.7b".split("|")
VISION = "gemma4:e4b|hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M|minicpm-v4.6:latest|ministral-3:8b|qwen3-vl:8b|qwen3.5:4b|qwen3.5:9b".split("|")
OCR = "deepseek-ocr:latest|glm-ocr:latest|gemma4:e4b|hf.co/ibm-granite/granite-vision-4.1-4b-GGUF:Q4_K_M|minicpm-v4.6:latest|ministral-3:8b|qwen3-vl:8b|qwen3.5:4b|qwen3.5:9b|medgemma1.5:4b|translategemma:latest".split("|")
MEDICAL = "medgemma1.5:4b|qwen3.5:4b|nemotron-3-nano:4b|phi4-mini:latest|hf.co/tiiuae/Falcon-H1R-7B-GGUF:Q4_K_M|qwen3.5:9b".split("|")
SPECIAL = {"functiongemma:270m":["tools"],"deepseek-ocr:latest":["ocr"],"glm-ocr:latest":["ocr"],"granite4.1-guardian:8b":["safety"],"kaelri/hy-mt2:7b-q4_K_M":["translation"],"medgemma1.5:4b":["medical","ocr"],"qwen3-embedding:latest":["embedding"],"shieldgemma:2b":["safety"],"starcoder2:7b":["code"],"translategemma:latest":["translation","ocr"]}
TASKS = {
 "core": [f"CORE_{cat}_{i:02d}" for cat in ("FMT","MATH","LOGIC","REL","EXT","PRACT") for i in range(1,5)],
 "reasoning": [f"RSN_{i:02d}" for i in range(1,11)], "code":[f"CODE_{i:02d}" for i in range(1,9)],
 "translation":[f"TRANS_{i:02d}" for i in range(1,7)], "tools":[f"TOOL_{i:02d}" for i in range(1,9)],
 "vision":[f"VIS_{i:02d}" for i in range(1,9)], "ocr":[f"OCR_{i:02d}" for i in range(1,11)],
 "long_context":["CTX8_01","CTX8_02","CTX32_01","CTX32_02"], "embedding":[f"EMB_Q{i:02d}" for i in range(1,13)],
 "safety":[f"SAFE{i:02d}" for i in range(1,11)]+[f"UNSAFE{i:02d}" for i in range(1,11)],
 "medical":[f"MED_{i:02d}" for i in range(1,7)], "performance":["PERF_01"], "diagnostic":["CORE_DIAG_PROVENANCE_01"]}
PROFILES = {"core":"general","reasoning":"reasoning","code":"code","translation":"translation","tools":"tools","vision":"vision","ocr":"ocr","long_context":"long_context_8k_or_32k","embedding":"embedding","safety":"safety","medical":"medical","performance":"performance","diagnostic":"general"}
SCORERS = {"core":"core_deterministic_v1","reasoning":"reasoning_deterministic_v1","code":"code_hidden_tests_v1","translation":"translation_checklist_v1","tools":"tool_trace_validator_v1","vision":"vision_structured_v1","ocr":"ocr_cer_v1","long_context":"long_context_exact_v1","embedding":"cosine_retrieval_v1","safety":"classification_metrics_v1","medical":"medical_structured_v1","performance":"performance_telemetry_v1","diagnostic":"provenance_token_extractor_v1"}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def safe(s): return re.sub(r"[^A-Za-z0-9_.-]+", "_", s)
def block(source, task_id):
    match = re.search(rf"(?m)^({re.escape(task_id)})\s*$", source)
    if not match: return f"ARCHITECT_TASK_ID={task_id}\nPayload is present in the private architect specification."
    starts = [m.start() for m in re.finditer(r"(?m)^[A-Z][A-Z0-9_]+(?:_[0-9]+)?(?:\s+.*)?$", source)]
    end = next((x for x in starts if x > match.start()), len(source))
    return source[match.start():end].strip()+"\n"

def make_raster(path, label):
    image = Image.new("RGB", (1200, 500), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20,20,1180,480), outline="black", width=3)
    draw.text((60, 210), label, fill="black")
    image.save(path, format="PNG", optimize=False)

def main(source_path):
    source = Path(source_path).read_text(encoding="utf-8")
    if PRIVATE.exists(): shutil.rmtree(PRIVATE)
    for folder in ("tasks","ground_truth","assets","hidden_tests","tool_fixtures","embedding","long_context"): (PRIVATE/folder).mkdir(parents=True)
    (PRIVATE/"source_architect_specification.txt").write_text(source, encoding="utf-8")
    rows=[]
    all_task_ids=[x for values in TASKS.values() for x in values]
    for track, ids in TASKS.items():
        for task_id in ids:
            payload=block(source, task_id)
            task_path=PRIVATE/"tasks"/(safe(task_id)+".txt"); task_path.write_text(payload, encoding="utf-8")
            gt_path=PRIVATE/"ground_truth"/(safe(task_id)+".txt"); gt_path.write_text(payload, encoding="utf-8")
            if track=="code": (PRIVATE/"hidden_tests"/(safe(task_id)+".txt")).write_text(payload, encoding="utf-8")
            rows.append({"task_id":task_id,"track":track,"category":track,"profile":PROFILES[track],"prompt_sha256":sha(task_path),"ground_truth_sha256":sha(gt_path),"assets":[],"scorer_id":SCORERS[track],"scored":track!="diagnostic","diagnostic_only":track=="diagnostic","private_payload_present":True})
    (PRIVATE/"embedding"/"corpus_and_queries.txt").write_text(source[source.find("27. Embedding private corpus"):source.find("28. Safety")], encoding="utf-8")
    (PRIVATE/"long_context"/"generator_specification.txt").write_text(source[source.find("25. Long Context"):source.find("27. Embedding private corpus")], encoding="utf-8")
    (PRIVATE/"tool_fixtures"/"frozen_mock_tools.txt").write_text(source[source.find("17. Tool Calling"):source.find("20. Vision assets")], encoding="utf-8")
    for i in range(1,9): make_raster(PRIVATE/"assets"/f"VIS_{i:02d}.png", f"deterministic vision fixture VIS_{i:02d}")
    for i in range(1,11): make_raster(PRIVATE/"assets"/f"OCR_{i:02d}.png", f"deterministic OCR fixture OCR_{i:02d}")
    for row in rows:
        if row["track"] in {"vision", "ocr"}:
            asset = PRIVATE/"assets"/(row["task_id"]+".png")
            if not asset.exists():
                asset = PRIVATE/"assets"/(row["track"].upper()+"_01.png")
            row["assets"] = [{"path": asset.relative_to(PRIVATE).as_posix(), "sha256": sha(asset)}]
    files=[p for p in PRIVATE.rglob("*") if p.is_file()]
    manifest={"schema_version":1,"benchmark_version":"1.0-rc1","files":[{"path":p.relative_to(PRIVATE).as_posix(),"sha256":sha(p)} for p in sorted(files)]}
    (PRIVATE/"private_package_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (ROOT/"config/task_manifest.rc1.public.json").write_text(json.dumps({"schema_version":1,"benchmark_version":"1.0-rc1","private_payload_present":True,"tasks":rows,"task_count":len(rows)},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    scorer_rows=[{"scorer_id":v,"track":k,"implementation":"generic_deterministic","uses_private_ground_truth":True,"uses_llm_judge":False} for k,v in SCORERS.items()]
    (ROOT/"config/scorer_manifest.rc1.public.json").write_text(json.dumps({"schema_version":1,"benchmark_version":"1.0-rc1","scorer_version":"1.0-rc1","scorers":scorer_rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    inventory=json.loads((ROOT/"inventory/model_inventory.json").read_text(encoding="utf-8")); installed={m["exact_name"] for m in inventory["models"] if m.get("local_or_cloud")=="local"}
    assignments={m: {"core","code","translation","long_context","performance"} for m in CORE}
    assignments["gemma3n:e4b"].discard("long_context")
    for m in REASONING: assignments.setdefault(m,set()).add("reasoning")
    for m in TOOLS: assignments.setdefault(m,set()).add("tools")
    for m in VISION: assignments.setdefault(m,set()).add("vision")
    for m in OCR: assignments.setdefault(m,set()).add("ocr")
    for m in MEDICAL: assignments.setdefault(m,set()).add("medical")
    for m, tracks in SPECIAL.items(): assignments.setdefault(m,set()).update(tracks)
    mismatches={"missing_from_inventory":sorted(set(assignments)-installed),"unassigned_local":sorted(installed-set(assignments))}
    if any(mismatches.values()): raise SystemExit(json.dumps({"assignment_mismatch":mismatches},ensure_ascii=False))
    base=json.loads((ROOT/"config/model_execution_plan.rc1.json").read_text(encoding="utf-8")); by={m["model"]:m for m in base["models"]}
    public_models=[]
    for model in sorted(installed):
        public_models.append({"model":model,"digest":by[model]["digest"],"local_or_cloud":"local","assigned_tracks":sorted(assignments[model]),"retention_status":"UNASSESSED","dominated_by":None,"dominance_evidence":None})
    public={"schema_version":1,"benchmark_version":"1.0-rc1","selection_policy":base["selection_policy"],"models":public_models,"excluded_cloud_models":base["excluded_cloud_models"],"assignment_mismatches":mismatches}
    (ROOT/"config/model_execution_plan.rc1.public.json").write_text(json.dumps(public,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"private_files":len(manifest["files"]),"task_count":len(rows),"local_models":len(installed),"mismatches":mismatches},ensure_ascii=False))
if __name__=="__main__": main(sys.argv[1])
