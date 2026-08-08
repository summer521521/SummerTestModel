"""Build public hashes/manifests from an already repaired private package."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; PRIVATE=ROOT/"private_benchmark/1.0-rc1"
TRACKS=["core","reasoning","code","translation","tools","vision","ocr","long_context","embedding","safety","medical","performance"]
ENTRYPOINT={"core":"score_core","reasoning":"score_reasoning","code":"score_code","translation":"score_translation","tools":"score_tools","vision":"score_vision","ocr":"score_ocr","long_context":"score_long_context","embedding":"score_embedding","safety":"score_safety","medical":"score_medical","performance":"score_performance","diagnostic":"score_diagnostic"}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    tasks=[]
    for p in sorted((PRIVATE/"tasks").glob("*.json")):
        task=json.loads(p.read_text(encoding="utf-8")); tid=task["task_id"]; gt=PRIVATE/"ground_truth"/p.name; spec=PRIVATE/"scoring_specs"/p.name; track=task["track"]
        assets=[]
        if track in {"vision","ocr"}:
            suffix="jpg" if tid=="OCR_09" else "png"; ap=PRIVATE/"assets"/(tid+"."+suffix); assets=[{"path":ap.relative_to(PRIVATE).as_posix(),"sha256":sha(ap)}]
        tasks.append({"task_id":tid,"version":task["version"],"track":track,"category":task["category"],"profile":task["profile"],"scorer_id":task["scorer_id"],"scored":track not in {"diagnostic","performance"},"diagnostic_only":track=="diagnostic","telemetry_only":track=="performance","prompt_sha256":hashlib.sha256(task["prompt"].encode("utf-8")).hexdigest(),"ground_truth_sha256":None if track in {"diagnostic","performance"} else sha(gt),"scoring_spec_sha256":sha(spec),"assets":assets,"private_payload_present":True})
    public_task={"schema_version":1,"benchmark_version":"1.0-rc1","tasks":tasks,"task_count":len(tasks),"scored_task_count":sum(x["scored"] for x in tasks),"diagnostic_task_count":sum(x["diagnostic_only"] for x in tasks),"telemetry_task_count":sum(x["telemetry_only"] for x in tasks)}
    tp=ROOT/"config/task_manifest.rc1.public.json"; tp.write_text(json.dumps(public_task,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    impl=sha(ROOT/"scripts/scorers.py"); scorer_rows=[{"scorer_id":f"{track}_deterministic_v1","track":track,"implementation":f"scripts/scorers.py:{ENTRYPOINT[track]}","sha256":impl,"private_scoring_spec":True,"uses_llm_judge":False} for track in TRACKS]+[{"scorer_id":"provenance_token_extractor_v1","track":"diagnostic","implementation":"scripts/scorers.py:score_diagnostic","sha256":impl,"private_scoring_spec":True,"uses_llm_judge":False}]
    sp=ROOT/"config/scorer_manifest.rc1.public.json"; sp.write_text(json.dumps({"schema_version":1,"benchmark_version":"1.0-rc1","scorer_version":"1.0-rc1","scorers":scorer_rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Convert the existing verified assignment list to the formal schema without changing assignments.
    old=json.loads((ROOT/"config/model_execution_plan.rc1.public.json").read_text(encoding="utf-8")); by={x["model"]:x for x in old["models"]}; model_rows=[]
    for model in old["models"]:
        tracks=model["assigned_tracks"]; ids=[x["task_id"] for x in tasks if x["track"] in tracks]; profiles=sorted(set(x["profile"] for x in tasks if x["track"] in tracks))
        model_rows.append({**model,"profiles":profiles,"task_ids":ids})
    plan={**old,"models":model_rows,"task_manifest_sha256":sha(tp),"scorer_manifest_sha256":sha(sp)}; mp=ROOT/"config/model_execution_plan.rc1.public.json"; mp.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    files=[p for p in PRIVATE.rglob("*") if p.is_file() and p.name!="private_package_manifest.json"]
    manifest={"schema_version":1,"benchmark_version":"1.0-rc1","files":[{"path":p.relative_to(PRIVATE).as_posix(),"sha256":sha(p)} for p in sorted(files)]}; pp=PRIVATE/"private_package_manifest.json"; pp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"task_manifest_sha256":sha(tp),"scorer_manifest_sha256":sha(sp),"model_plan_sha256":sha(mp),"private_package_sha256":sha(pp),"counts":{"total":len(tasks),"scored":public_task["scored_task_count"],"diagnostic":public_task["diagnostic_task_count"],"telemetry":public_task["telemetry_task_count"]}},ensure_ascii=False))
if __name__=="__main__": main()
