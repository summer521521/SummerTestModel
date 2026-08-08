"""Integrity validator for the RC1 private/public freeze package."""
from __future__ import annotations
import json, hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ALLOWED_PROFILES={"general","reasoning","code","translation","tools","vision","ocr","safety","medical","long_context_8k","long_context_32k","embedding","performance"}
ALLOWED_CATEGORIES={"format_instruction","arithmetic","logic","reliability","extraction","practical","provenance_diagnostic","reasoning","code","translation","tools","vision","ocr","long_context","embedding","safety","medical","performance"}

def _sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def validate(root=ROOT):
    errors=[]; metrics={"prompt_gt_identical_before_or_current":0,"private_payload_identical":0,"placeholder_assets":0,"missing_structured_code_tests":0,"invalid_category_or_profile":0,"schema_errors":0}
    task_path=root/"config/task_manifest.rc1.public.json"; scorer_path=root/"config/scorer_manifest.rc1.public.json"
    try: tasks=json.loads(task_path.read_text(encoding="utf-8"))["tasks"]
    except Exception as exc: return {"valid":False,"errors":[f"task_manifest: {exc}"],"metrics":metrics}
    for task in tasks:
        if task.get("scored") and task.get("prompt_sha256")==task.get("ground_truth_sha256"):
            metrics["prompt_gt_identical_before_or_current"]+=1
        if task.get("category") not in ALLOWED_CATEGORIES or task.get("profile") not in ALLOWED_PROFILES and not (task.get("track")=="long_context" and task.get("profile") in {"long_context_8k_or_32k"}):
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
                if len(json.loads(p.read_text(encoding="utf-8")).get("cases",[]))!=10: metrics["missing_structured_code_tests"]+=1
            except Exception: metrics["missing_structured_code_tests"]+=1
    try:
        scorer=json.loads(scorer_path.read_text(encoding="utf-8"))
        for item in scorer.get("scorers",[]):
            for key in ("scorer_id","implementation","sha256"):
                if not item.get(key): metrics["schema_errors"]+=1
    except Exception: metrics["schema_errors"]+=1
    if metrics["prompt_gt_identical_before_or_current"] or metrics["private_payload_identical"] or metrics["placeholder_assets"] or metrics["missing_structured_code_tests"] or metrics["invalid_category_or_profile"] or metrics["schema_errors"]:
        errors.append("RC1 freeze integrity defects detected")
    return {"valid":not errors,"errors":errors,"metrics":metrics}

if __name__=="__main__": print(json.dumps(validate(),ensure_ascii=False,indent=2))
