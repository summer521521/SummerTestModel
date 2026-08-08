"""Deterministic context generator; target values are loaded from private spec."""
from __future__ import annotations
import json, random, sys
from pathlib import Path

def generate(spec_path, out_dir):
    specs=json.loads(Path(spec_path).read_text(encoding="utf-8")); out=Path(out_dir); out.mkdir(parents=True,exist_ok=True); records=[]
    for spec in specs:
        rng=random.Random(20260808+sum(map(ord,spec["task_id"]))); target=spec["target_id"]; answer=spec["answer"]
        count=5000 if spec["tier"]=="8k" else 20000
        tokens=[f"record{i:05d}" if j%7==0 else f"field{j%31}" for i in range(count) for j in [i]]
        position=0.15 if spec["task_id"].endswith("01") else (0.90 if spec["task_id"].endswith("02") and spec["tier"]=="32k" else 0.85)
        index=max(0,min(count-1,int(count*position)))
        tokens[index:index]=[f"target_id={target}",f"target_field={answer}"]
        payload=" ".join(tokens)+"\n"; path=out/(spec["task_id"]+".txt"); path.write_text(payload,encoding="utf-8")
        token_count=len(payload.split()); target_pos=payload.split().index(f"target_id={target}")/token_count
        records.append({"task_id":spec["task_id"],"path":path.name,"character_count":len(payload),"whitespace_token_count":token_count,"target_occurrences":payload.count(target),"target_position_fraction":target_pos})
    (out/"metadata.json").write_text(json.dumps(records,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return records
if __name__=="__main__": print(json.dumps(generate(sys.argv[1],sys.argv[2]),ensure_ascii=False,indent=2))
