"""Repair the RC1 freeze into separated private JSON payloads.

Inputs are the already captured private Phase 3 architect source and the
Phase 4 repair specification. No prompt or answer literals live in this
tracked script; they are parsed into the ignored package.
"""
from __future__ import annotations
import ast, hashlib, json, re, shutil, sys
from pathlib import Path
try:
    from scripts.freeze_phase3_private import TASKS, PROFILES, SCORERS, CORE, REASONING, TOOLS, VISION, OCR, MEDICAL, SPECIAL, block as old_block
except ModuleNotFoundError:
    from freeze_phase3_private import TASKS, PROFILES, SCORERS, CORE, REASONING, TOOLS, VISION, OCR, MEDICAL, SPECIAL, block as old_block

ROOT=Path(__file__).resolve().parents[1]; PRIVATE=ROOT/"private_benchmark/1.0-rc1"

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def clean_id(value): return re.sub(r"[^A-Za-z0-9_.-]+","_",value)

def source_block(source, tid):
    return old_block(source, tid)

def prompt_and_truth(raw):
    raw=raw.strip()
    raw=re.sub(r"^[-=]+\s*", "", raw)
    # Remove the task-id heading while preserving the architect wording.
    raw=re.sub(r"^[A-Z][A-Z0-9_]+(?:\s+[^\n]*)?\n", "", raw, count=1)
    marker=re.search(r"(?m)^\s*(?:Ground truth(?: semantic set)?|GT(?: accepted)?|Truth|Expected)[:：]", raw)
    if marker:
        prompt=raw[:marker.start()].strip()
        tail=raw[marker.end():]
        tail=re.split(r"\n(?:Scoring|Tolerance|accept|Order-insensitive|Rules|============================================================|-----------------------)\b",tail,maxsplit=1)[0].strip()
        return prompt, tail
    marker=re.search(r"(?m)^\s*Expected:\s*$", raw)
    if marker: return raw[:marker.start()].strip(), raw[marker.end():].strip()
    return raw, None

def truth_from_source(source, tid):
    raw=source_block(source,tid); prompt,truth=prompt_and_truth(raw)
    return truth

def code_vectors(repair_source, tid):
    raw=source_block(repair_source,tid)
    function=(re.search(r"(?m)^CODE_\d+\s+([A-Za-z_][A-Za-z0-9_]*)",raw) or [None,"unknown"])[1]
    pieces=re.split(r"(?m)^T(\d+)(?::|\s)",raw)[1:]
    cases=[]
    for i in range(0,len(pieces),2):
        if i+1>=len(pieces): break
        body=pieces[i+1].strip(); nxt=re.search(r"\nT\d+\s*$",body)
        if nxt: body=body[:nxt.start()].strip()
        expected=None
        match=re.search(r"(?m)(?:expected\s*=|->)\s*(.+)$",body)
        if match: expected=match.group(1).strip()
        cases.append({"case_id":f"T{pieces[i]}","input":body,"expected":expected,"source_sha256":hashlib.sha256(body.encode()).hexdigest()})
    return {"function":function,"cases":cases[:10]}

def parse_section_records(source, prefix):
    result=[]
    matches=list(re.finditer(rf"(?m)^({prefix}\d+)\s+([^\n]*)\n",source))
    for i,m in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(source)
        result.append((m.group(1),m.group(2).strip(),source[m.end():end].strip()))
    return result

def parse_embedding(source):
    section=source[source.find("27. Embedding private corpus"):source.find("28. Safety")]
    docs=[]
    for m in re.finditer(r"(?ms)^D(\d+)\s*\n(.*?)(?=^D\d+\s*$|^Decoys|^Queries)",section): docs.append({"doc_id":"D"+m.group(1),"text":m.group(2).strip()})
    queries=[]
    for m in re.finditer(r"(?ms)^Q(\d+)\s*\n(.*?)->\s*(D\d+)",section):
        text=m.group(2).strip().splitlines()[0].strip(); queries.append({"query_id":"Q"+m.group(1),"text":text,"relevant_doc_ids":[m.group(3)]})
    return docs,queries

def parse_safety(source):
    section=source[source.find("28. Safety"):source.find("29. Medical")]
    records=[]
    matches=list(re.finditer(r"(?m)^(SAFE|UNSAFE)(\d+)\s+(safe|unsafe)\s*$",section))
    for i,m in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(section)
        records.append({"task_id":m.group(1)+m.group(2),"text":section[m.end():end].strip(),"label":m.group(3)})
    return records

def parse_long_context(source):
    section=source[source.find("25. Long Context"):source.find("26. Long-context assignments")]
    specs=[]
    for tid,tier in (("CTX8_01","8k"),("CTX8_02","8k"),("CTX32_01","32k"),("CTX32_02","32k")):
        m=re.search(rf"(?ms)^({tid})\s*\n-----------------------\s*\n(.*?)(?=^CTX|\Z)",section)
        raw=m.group(2) if m else ""
        pairs=re.findall(r"(?:Target|target).*?id\s*=\s*([A-Z]{2}-\d+).*?(?:code|owner|status|checksum field)\s*=\s*([^\n]+)",raw,re.S|re.I)
        target_id=pairs[0][0] if pairs else None; answer=pairs[0][1].strip() if pairs else None
        specs.append({"task_id":tid,"tier":tier,"target_id":target_id,"answer":answer,"raw_spec":raw.strip()})
    return specs

def make_specs(source, tid, track):
    if track=="diagnostic": return {"type":"diagnostic","diagnostic_only":True}
    types={"core":"deterministic_core","reasoning":"deterministic_reasoning","code":"code_hidden_tests","translation":"translation_checklist","tools":"tool_trace","vision":"vision_exact","ocr":"ocr_cer","long_context":"long_context_exact","embedding":"embedding_retrieval","safety":"classification_metrics","medical":"medical_structured","performance":"telemetry_only"}
    return {"scorer_id":SCORERS[track],"type":types[track],"private_ground_truth":True,"uses_llm_judge":False,"protocol_required":track=="core"}

def main(repair_source_path):
    source_path=PRIVATE/"source_architect_specification.txt"; source=source_path.read_text(encoding="utf-8"); repair_source=Path(repair_source_path).read_text(encoding="utf-8")
    folders=["tasks","ground_truth","scoring_specs","hidden_tests","tool_fixtures","embedding","long_context","safety","assets"]
    for folder in folders: shutil.rmtree(PRIVATE/folder,ignore_errors=True); (PRIVATE/folder).mkdir(parents=True)
    # Structured task/GT/spec files. GT never contains the prompt.
    rows=[]
    for track,ids in TASKS.items():
        for tid in ids:
            raw=source_block(source,tid) if not tid.startswith(("EMB_","SAFE","UNSAFE")) else ""
            if track=="safety":
                record=next(x for x in parse_safety(source) if x["task_id"]==tid); prompt=record["text"]; gt={"label":record["label"]}
            elif track=="embedding":
                docs,queries=parse_embedding(source); record=next(x for x in queries if x["query_id"]==tid.replace("EMB_","")) if False else None
                qid=tid.replace("EMB_",""); query=next((x for x in queries if x["query_id"]==qid),{"text":tid,"relevant_doc_ids":[]}); prompt=query["text"]; gt={"relevant_doc_ids":query["relevant_doc_ids"]}
            elif track=="performance":
                section=source[source.find("30. Performance"):source.find("31. Core model assignment")]; match=re.search(r"(?ms)Prompt exact:\s*\n(.*?)\nProfile:",section); prompt=(match.group(1).strip() if match else section.strip()); gt=None
            elif tid=="CORE_DIAG_PROVENANCE_01": prompt,gt=prompt_and_truth(source_block(source,tid)); gt=None
            elif track=="code": prompt,gt=prompt_and_truth(raw); gt={"hidden_tests":f"hidden_tests/{tid}.json"}
            else: prompt,truth=prompt_and_truth(raw); gt={"value":truth}
            task={"task_id":tid,"version":"1.0-rc1","track":track,"category":({"FMT":"format_instruction","MATH":"arithmetic","LOGIC":"logic","REL":"reliability","EXT":"extraction","PRACT":"practical"}.get(tid.split("_")[1],track) if track=="core" else "provenance_diagnostic" if track=="diagnostic" else track),"profile":("long_context_8k" if tid.startswith("CTX8") else "long_context_32k" if tid.startswith("CTX32") else PROFILES[track]),"prompt":prompt,"scorer_id":SCORERS[track],"diagnostic_only":track=="diagnostic"}
            tp=PRIVATE/"tasks"/(tid+".json"); gp=PRIVATE/"ground_truth"/(tid+".json"); sp=PRIVATE/"scoring_specs"/(tid+".json")
            tp.write_text(json.dumps(task,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); gp.write_text(json.dumps(gt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); sp.write_text(json.dumps(make_specs(source,tid,track),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            rows.append({"task_id":tid,"version":"1.0-rc1","track":task["track"],"category":task["category"],"profile":task["profile"],"scorer_id":SCORERS[track],"scored":track not in {"diagnostic","performance"},"diagnostic_only":track=="diagnostic","telemetry_only":track=="performance","prompt_sha256":sha(tp),"ground_truth_sha256":None if track=="diagnostic" else sha(gp),"scoring_spec_sha256":sha(sp),"assets":[],"private_payload_present":True})
    # Exact architect code vectors are parsed from the repair task book, not hardcoded here.
    for i in range(1,9): (PRIVATE/"hidden_tests"/(f"CODE_{i:02d}.json")).write_text(json.dumps(code_vectors(repair_source,f"CODE_{i:02d}"),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    docs,queries=parse_embedding(source); (PRIVATE/"embedding/corpus.json").write_text(json.dumps(docs,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); (PRIVATE/"embedding/queries.json").write_text(json.dumps(queries,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (PRIVATE/"safety/tasks.json").write_text(json.dumps(parse_safety(source),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (PRIVATE/"long_context/spec.json").write_text(json.dumps(parse_long_context(source),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    tools_section=source[source.find("17. Tool Calling"):source.find("19. Tool assignment")]
    tool_records=[]
    for tid,_,raw in parse_section_records(source,"TOOL_"):
        if tid not in {f"TOOL_{i:02d}" for i in range(1,9)}: continue
        calls=re.findall(r"(?m)^\s*([a-z_]+)(?::|\s+call)",raw)
        tool_records.append({"task_id":tid,"expected_tool_calls":calls,"source_spec_sha256":hashlib.sha256(raw.encode()).hexdigest(),"extra_unrelated_call_fails":True})
    (PRIVATE/"tool_fixtures/tasks.json").write_text(json.dumps(tool_records,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (PRIVATE/"tool_fixtures/tools.json").write_text(json.dumps({"source_spec_sha256":hashlib.sha256(tools_section.encode()).hexdigest(),"tools":[{"name":n} for n in re.findall(r"(?m)^([a-z_]+)\s*$",tools_section)]},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Replace assets with structured private specs; rendering is delegated to public generic engine.
    asset_specs=[]
    for tid in [f"VIS_{i:02d}" for i in range(1,9)]+[f"OCR_{i:02d}" for i in range(1,11)]:
        raw=source_block(source,tid); asset_specs.append({"asset_id":tid,"source_spec_sha256":hashlib.sha256(raw.encode()).hexdigest(),"render_text":raw,"format":"JPEG" if tid=="OCR_09" else "PNG","width":1024,"height":768})
    (PRIVATE/"assets/specs.json").write_text(json.dumps(asset_specs,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"tasks":len(rows),"code_hidden_tests":8,"embedding_docs":len(docs),"embedding_queries":len(queries),"safety":len(parse_safety(source))},ensure_ascii=False))

def code_vectors(repair_source,tid):
    matches=list(re.finditer(r"(?m)^CODE_(\d+)(?:\s+([^\n]+))?\s*$",repair_source)); match=next((m for m in matches if "CODE_"+m.group(1)==tid),None)
    if not match: return {"function":"unknown","cases":[]}
    end=next((m.start() for m in matches if m.start()>match.start()),len(repair_source)); raw=repair_source[match.start():end]; fn=match.group(2).strip() if match.group(2) else "unknown"; pieces=re.split(r"(?m)^T(\d+)(?::|\s)",raw)[1:]; cases=[]
    for i in range(0,len(pieces),2):
        if i+1>=len(pieces): break
        body=pieces[i+1].strip(); cases.append({"case_id":f"T{pieces[i]}","case_text":body,"source_sha256":hashlib.sha256(body.encode()).hexdigest()})
    return {"function":fn,"cases":cases[:10]}

if __name__=="__main__": main(sys.argv[1])
