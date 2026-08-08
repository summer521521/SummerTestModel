"""Deterministic context generator; target values are loaded from private spec."""
from __future__ import annotations
import json, random, sys
from pathlib import Path

def generate(spec_path, out_dir):
    specs=json.loads(Path(spec_path).read_text(encoding="utf-8")); out=Path(out_dir); out.mkdir(parents=True,exist_ok=True); records=[]
    for spec in specs:
        rng=random.Random(20260808+sum(map(ord,spec["task_id"]))); target=spec["target_id"]; answer=spec["answer"]; count=450 if spec["tier"]=="8k" else 1800
        lines=[f"REC-{i:05d} owner=Owner{i%17:02d} code=CODE-{i%23:02d} status=stable zone=Z{i%11:02d} note=stable." for i in range(count)]
        position=0.15 if spec["task_id"].endswith("01") else 0.85; index=max(0,min(count-1,int(count*position)))
        field="code" if "8_01" in spec["task_id"] else "owner" if "8_02" in spec["task_id"] else "status" if "32_01" in spec["task_id"] else "checksum"
        lines[index]=f"REC-TARGET owner=Rhea code={answer} status={answer} checksum={answer} id={target} field={field}."
        payload="\n".join(lines)+"\n"; path=out/(spec["task_id"]+".txt"); path.write_text(payload,encoding="utf-8")
        records.append({"task_id":spec["task_id"],"path":path.name,"character_count":len(payload),"target_occurrences":payload.count(target),"target_position_fraction":payload.find(target)/len(payload)})
    (out/"metadata.json").write_text(json.dumps(records,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return records
if __name__=="__main__": print(json.dumps(generate(sys.argv[1],sys.argv[2]),ensure_ascii=False,indent=2))
