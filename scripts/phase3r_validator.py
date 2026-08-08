"""Integrity validator for the RC1 private/public freeze package."""
from __future__ import annotations
import json, hashlib, importlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ALLOWED_PROFILES={"general","reasoning","code","translation","tools","vision","ocr","safety","medical","long_context_8k","long_context_32k","embedding","performance"}
ALLOWED_CATEGORIES={"format_instruction","arithmetic","logic","reliability","extraction","practical","provenance_diagnostic","reasoning","code","translation","tools","vision","ocr","long_context","embedding","safety","medical","performance"}

def _sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def validate(root=ROOT):
    errors=[]; metrics={"prompt_gt_identical_before_or_current":0,"private_payload_identical":0,"placeholder_assets":0,"missing_structured_code_tests":0,"invalid_category_or_profile":0,"schema_errors":0,"scorer_referential_errors":0}
    task_path=root/"config/task_manifest.rc1.public.json"; scorer_path=root/"config/scorer_manifest.rc1.public.json"
    try: tasks=json.loads(task_path.read_text(encoding="utf-8"))["tasks"]
    except Exception as exc: return {"valid":False,"errors":[f"task_manifest: {exc}"],"metrics":metrics}
    for task in tasks:
        if task.get("scored") and task.get("prompt_sha256")==task.get("ground_truth_sha256"):
            metrics["prompt_gt_identical_before_or_current"]+=1
        if (task.get("category") not in ALLOWED_CATEGORIES) or (task.get("profile") not in ALLOWED_PROFILES):
            metrics["invalid_category_or_profile"]+=1
    private=root/"private_benchmark/1.0-rc1"
    for task in tasks:
        tid=task["task_id"]; tp=private/"tasks"/(tid+".json"); gp=private/"ground_truth"/(tid+".json")
        if not tp.is_file() or not gp.is_file(): metrics["private_payload_identical"]+=1; continue
        if tp.read_bytes()==gp.read_bytes(): metrics["private_payload_identical"]+=1
    for p in list((private/"assets").glob("*.png"))+list((private/"assets").glob("*.jpg")):
        try:
            from PIL import Image
            with Image.open(p) as image:
                if image.size != (1024, 768):
                    metrics["placeholder_assets"] += 1
        except Exception: metrics["placeholder_assets"]+=1
    for i in range(1,9):
        p=private/"hidden_tests"/(f"CODE_{i:02d}.json")
        if not p.is_file(): metrics["missing_structured_code_tests"]+=1
        else:
            try:
                data=json.loads(p.read_text(encoding="utf-8")); cases=data.get("cases",[])
                if len(cases)!=10 or not data.get("function") or any(not isinstance(c.get("args"),list) or not isinstance(c.get("kwargs"),dict) or "expected" not in c for c in cases): metrics["missing_structured_code_tests"]+=1
            except Exception: metrics["missing_structured_code_tests"]+=1
    try:
        scorer=json.loads(scorer_path.read_text(encoding="utf-8")); by_id={x.get("scorer_id"):x for x in scorer.get("scorers",[])}
        for item in scorer.get("scorers",[]):
            for key in ("scorer_id","implementation","sha256"):
                if not item.get(key): metrics["schema_errors"]+=1
        for task in tasks:
            item=by_id.get(task.get("scorer_id"))
            if not item or item.get("track")!=task.get("track"):
                metrics["scorer_referential_errors"]+=1; continue
            implementation=item.get("implementation","")
            try:
                module_path,entrypoint=implementation.split(":",1); module_name=module_path[:-3].replace("/",".").replace("\\",".")
                try: module=importlib.import_module(module_name)
                except ModuleNotFoundError: module=importlib.import_module(module_name.rsplit(".",1)[-1])
                if not callable(getattr(module,entrypoint,None)): metrics["scorer_referential_errors"]+=1
            except Exception: metrics["scorer_referential_errors"]+=1
    except Exception: metrics["schema_errors"]+=1
    if any(metrics.values()):
        errors.append("RC1 freeze integrity defects detected")
    return {"valid":not errors,"errors":errors,"metrics":metrics}

if __name__=="__main__": print(json.dumps(validate(),ensure_ascii=False,indent=2))
