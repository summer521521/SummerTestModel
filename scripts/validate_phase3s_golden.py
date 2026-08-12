"""Offline Phase 3S golden gate; reads only the ignored private package."""
from __future__ import annotations
import json
from pathlib import Path
try:
    from scripts.scorers import score_task
except ModuleNotFoundError:
    from scorers import score_task

ROOT=Path(__file__).resolve().parents[1]; PRIVATE=ROOT/"private_benchmark/1.0-rc1"
REFERENCE={
"rotate_left": "def rotate_left(items,k):\n    if not items:return []\n    k%=len(items)\n    return items[k:]+items[:k]\n",
"balanced_brackets": "def balanced_brackets(text):\n    pairs={')':'(',']':'[','}':'{'}; stack=[]\n    for ch in text:\n        if ch in '([{': stack.append(ch)\n        elif ch in pairs:\n            if not stack or stack.pop()!=pairs[ch]: return False\n    return not stack\n",
"merge_intervals": "def merge_intervals(intervals):\n    out=[]\n    for a,b in sorted(intervals):\n        if out and a<=out[-1][1]: out[-1][1]=max(out[-1][1],b)\n        else: out.append([a,b])\n    return out\n",
"rle_encode": "def rle_encode(s):\n    if not s:return []\n    out=[]; last=s[0]; n=0\n    for ch in s:\n        if ch==last:n+=1\n        else:out.append([last,n]); last=ch; n=1\n    out.append([last,n]); return out\n",
"first_unique_index": "def first_unique_index(s):\n    for i,ch in enumerate(s):\n        if s.count(ch)==1:return i\n    return -1\n",
"top_k_frequent": "def top_k_frequent(items,k):\n    counts={}\n    for x in items: counts[x]=counts.get(x,0)+1\n    return [x for x,n in sorted(counts.items(),key=lambda z:(-z[1],z[0]))[:max(0,k)]]\n",
"parse_kv_lines": "def parse_kv_lines(text):\n    out={}\n    for line in text.splitlines():\n        if '=' in line:\n            k,v=line.split('=',1); out[k.strip()]=v.strip()\n    return out\n",
"free_slots": "def free_slots(intervals,start,end):\n    clipped=sorted((max(start,a),min(end,b)) for a,b in intervals if min(end,b)>max(start,a)); out=[]; cur=start\n    for a,b in clipped:\n        if a>cur:out.append([cur,a])\n        cur=max(cur,b)\n    if cur<end:out.append([cur,end])\n    return out\n",
}

def load(path): return json.loads(path.read_text(encoding="utf-8"))

def golden_evidence(task,gt,spec):
    track=task["track"]; tid=task["task_id"]
    if track=="code":
        return {"final_answer":REFERENCE[gt["function"]]}
    if track=="translation":
        return {"final_answer":" ".join(x.get("golden_fragment","") for x in spec["components"] if x.get("golden_fragment"))}
    if track=="tools":
        facts=list(gt["required_final_facts"]); any_of=gt.get("required_final_any_of",[])
        if any_of: facts.append(any_of[0])
        return {"tool_calls":gt["expected_calls"],"tool_results":[{"ok":True} for _ in gt["expected_calls"]],"final_answer":" ".join(facts),"clarification":bool(gt["clarification_required"])}
    if track=="embedding":
        relevant=gt["relevant_doc_ids"][0]; docs=[x["doc_id"] for x in load(PRIVATE/"embedding/corpus.json")]
        return {"corpus_embeddings":{doc:([1.0,0.0] if doc==relevant else [0.0,1.0]) for doc in docs},"query_embedding":[1.0,0.0]}
    if track=="safety":
        unsafe=str(gt["label"]).lower()=="unsafe"
        return {"final_answer":"Yes" if unsafe else "No","model":"shieldgemma:2b"}
    if tid=="MED_01": return {"final_answer":json.dumps(gt["records"],ensure_ascii=False,separators=(",",":"))}
    return {"final_answer":str(gt.get("value",""))}

def is_full(track,result):
    if track=="core": return result.get("task_score")==1.0
    if track=="reasoning": return result.get("task_score")==1.0
    if track=="code": return result.get("score")==1.0 and result.get("passed_tests")==10
    if track=="translation": return result.get("normalized_score_0_to_1")==1.0
    if track=="tools": return result.get("exact_task_success")==1
    if track=="ocr": return result.get("exact_match") is True and result.get("char_accuracy")==1.0
    if track=="embedding": return all(result.get(k)==1.0 for k in ("recall_at_1","recall_at_3","recall_at_5","mrr","ndcg_at_5"))
    if track=="safety": return result.get("accuracy")==1.0 and result.get("invalid_response_count")==0
    return result.get("score")==1.0

def wrong_evidence(task,gt,spec):
    track=task["track"]
    if track=="code": return {"final_answer":f"def {gt['function']}(*args, **kwargs):\n    return None\n"}
    if track=="tools": return {"tool_calls":[{"name":"nonexistent","arguments":{}}],"final_answer":"","clarification":False}
    if track=="embedding":
        docs=[x["doc_id"] for x in load(PRIVATE/"embedding/corpus.json")]; relevant=gt["relevant_doc_ids"][0]; wrong=next(x for x in docs if x!=relevant)
        return {"corpus_embeddings":{doc:([1.0,0.0] if doc==wrong else [0.0,1.0]) for doc in docs},"query_embedding":[1.0,0.0]}
    if track=="safety": return {"final_answer":"No" if str(gt["label"]).lower()=="unsafe" else "Yes","model":"shieldgemma:2b"}
    return {"final_answer":"__WRONG_FIXTURE__"}

def main():
    public=load(ROOT/"config/task_manifest.rc1.public.json"); rows=[]; wrong_by_family={}; code_cases=0
    for row in public["tasks"]:
        if not row["scored"]: continue
        tid=row["task_id"]; task=load(PRIVATE/"tasks"/(tid+".json")); gt=load(PRIVATE/"ground_truth"/(tid+".json")); spec=load(PRIVATE/"scoring_specs"/(tid+".json"))
        result=score_task(golden_evidence(task,gt,spec),task,gt,spec); full=is_full(task["track"],result)
        rows.append({"task_id":tid,"track":task["track"],"full":full})
        if task["track"]=="code": code_cases+=result.get("total_tests",0)
        if task["track"] not in wrong_by_family:
            wrong=score_task(wrong_evidence(task,gt,spec),task,gt,spec); wrong_by_family[task["track"]]=not is_full(task["track"],wrong)
    aggregate={"schema_version":1,"benchmark_version":"1.0-rc1","tasks_checked":len(rows),"full_score_pass":sum(x["full"] for x in rows),"failures":[{"task_id":x["task_id"],"track":x["track"]} for x in rows if not x["full"]],"code_cases_checked":code_cases,"wrong_fixture_families_checked":len(wrong_by_family),"wrong_fixture_failures":[track for track,passed in wrong_by_family.items() if not passed]}
    (ROOT/"handoff/scorer_golden_validation.json").write_text(json.dumps(aggregate,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(aggregate,ensure_ascii=False))
    raise SystemExit(0 if aggregate["full_score_pass"]==aggregate["tasks_checked"] and not aggregate["wrong_fixture_failures"] else 1)
if __name__=="__main__": main()
