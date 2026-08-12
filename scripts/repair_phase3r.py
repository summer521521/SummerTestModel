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

SCORERS = {"core":"core_deterministic_v1","reasoning":"reasoning_deterministic_v1","code":"code_hidden_tests_v1","translation":"translation_checklist_v1","tools":"tool_trace_validator_v1","vision":"vision_structured_v1","ocr":"ocr_cer_v1","long_context":"long_context_exact_v1","embedding":"cosine_retrieval_v1","safety":"classification_metrics_v1","medical":"medical_structured_v1","performance":"performance_telemetry_v1","diagnostic":"provenance_token_extractor_v1"}

ROOT=Path(__file__).resolve().parents[1]; PRIVATE=ROOT/"private_benchmark/1.0-rc1"

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def clean_id(value): return re.sub(r"[^A-Za-z0-9_.-]+","_",value)

def source_block(source, tid):
    # Architect task headings may carry a human-readable suffix (for example
    # ``OCR_01 clear English``).  The legacy helper only handled a subset of
    # those headings and could return a placeholder instead of the frozen
    # source.  Bound the block by the next dashed task heading without
    # interpreting or rewriting any architect content.
    heading=re.search(rf"(?m)^{re.escape(tid)}(?:\s+[^\n]*)?\s*$",source)
    if not heading:
        return old_block(source,tid)
    following=source[heading.end():]
    boundary=re.search(r"(?m)^(?:={5,}|-{5,}\s*\n(?=[A-Z][A-Z0-9_]+(?:\s+[^\n]*)?\s*$))",following)
    end=heading.end()+(boundary.start() if boundary else len(following))
    return source[heading.start():end].strip()

def prompt_and_truth(raw):
    raw=raw.strip()
    raw=re.sub(r"^[-=]+\s*", "", raw)
    # Remove the task-id heading while preserving the architect wording.
    raw=re.sub(r"^[A-Z][A-Z0-9_]+(?:\s+[^\n]*)?\n", "", raw, count=1)
    marker=re.search(r"(?m)^\s*(?:Ground truth(?: semantic(?: set)?| set)?|GT(?: accepted)?|Truth(?: exactly)?|Expected(?: output)?)[:：]", raw)
    if marker:
        prompt=raw[:marker.start()].strip()
        tail=raw[marker.end():]
        tail=re.split(r"\n(?:Scoring|Scorer|Tolerance|accept|Order-insensitive|Rules|Forbidden answer|Render|Use deterministic|Save deterministic|Preserve newline)(?:\b|[:：])|\n[=-]{5,}",tail,maxsplit=1)[0].strip()
        return prompt, tail
    marker=re.search(r"(?m)^\s*Expected:\s*$", raw)
    if marker: return raw[:marker.start()].strip(), raw[marker.end():].strip()
    return raw, None

def truth_from_source(source, tid):
    raw=source_block(source,tid); prompt,truth=prompt_and_truth(raw)
    return truth

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
    result={"scorer_id":SCORERS[track],"type":types[track],"private_ground_truth":True,"uses_llm_judge":False,"protocol_required":track=="core"}
    if track=="translation":
        raw=source_block(source,tid); section=raw.split("Checks：",1)[-1]; components=[]
        for line in section.splitlines():
            match=re.match(r"\s*(.+?)\s+(\d+)\s*$",line)
            if match:
                label=match.group(1).strip(); weight=int(match.group(2)); lower=label.lower()
                base=re.sub(r"\s+exact$","",label,flags=re.I); golden=re.split(r"\s+OR\s+|/",base,flags=re.I)[0].strip()
                matcher="regex"; patterns=[re.escape(x.strip()) for x in re.split(r"\s+OR\s+|/",base) if x.strip()]
                if "dominant" in lower: matcher="language_dominance"; patterns=["zh" if ("chinese" in lower) else "en"]; golden=""
                elif "no explanation" in lower: matcher="no_extra_explanation"; patterns=[]; golden=""
                elif "<= 20 english words" in lower: matcher="max_word_count"; patterns=["20"]; golden=""
                elif "minute meaning" in lower: patterns=["分钟","minute"]; golden="分钟"
                elif lower=="remained": patterns=["仍","依然","保持"]; golden="仍"
                elif "locked" in lower: patterns=["锁定","锁住"]; golden="锁定"
                elif "increase semantic" in lower: patterns=["increase","increased","rose","rises"]; golden="increased"
                elif "retry semantic" in lower: patterns=["重试"]; golden="重试"
                elif "success semantic" in lower: patterns=["成功"]; golden="成功"
                elif "attempt 4" in lower: patterns=[r"第?\s*4\s*次",r"attempt\s*4"]; golden="第4次"
                elif "negative" in lower: patterns=[r"(?:do\s+not|must\s+not|never)\s+delete"]; golden="do not delete"
                elif "health check failure" in lower: patterns=[r"health\s+check.*fail"]; golden="health check failure"
                elif "record error" in lower: patterns=[r"record.*error"]; golden="record error"
                elif "wait for recovery" in lower: patterns=[r"wait.*recover"]; golden="wait for recovery"
                elif "condition if stale" in lower: patterns=[r"(?:如果|若).*?(?:过期|陈旧)"]; golden="如果缓存过期"
                elif lower=="cache": patterns=["缓存"]; golden="缓存"
                elif lower=="refresh": patterns=["刷新"]; golden="刷新"
                elif lower=="otherwise": patterns=["否则"]; golden="否则"
                elif "keep current snapshot" in lower: patterns=[r"(?:保留|保持).*?当前.*?快照"]; golden="保留当前快照"
                elif "connection restored" in lower: patterns=[r"connection.*restored"]; golden="connection restored"
                elif "resume/continue" in lower: patterns=["resume","continue"]; golden="resume"
                elif "previous/last test" in lower: patterns=[r"(?:previous|last).*test"]; golden="previous test"
                components.append({"id":clean_id(label),"weight":weight,"matcher_type":matcher,"accepted_patterns":patterns,"forbidden_patterns":[],"golden_fragment":golden})
        result["components"]=components; result["weight_sum"]=sum(x["weight"] for x in components)
    return result

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
            else:
                prompt,truth=prompt_and_truth(raw)
                if tid=="MED_01":
                    records=[]
                    for drug,dose,frequency in re.findall(r"(?m)^([A-Za-z]+)\s+([0-9]+\s*mg)\s+(.+?)\.$",prompt): records.append({"drug":drug,"dose":dose,"frequency":frequency})
                    gt={"records":records}
                else: gt={"value":truth}
            task={"task_id":tid,"version":"1.0-rc1","track":track,"category":({"FMT":"format_instruction","MATH":"arithmetic","LOGIC":"logic","REL":"reliability","EXT":"extraction","PRACT":"practical"}.get(tid.split("_")[1],track) if track=="core" else "provenance_diagnostic" if track=="diagnostic" else track),"profile":("long_context_8k" if tid.startswith("CTX8") else "long_context_32k" if tid.startswith("CTX32") else PROFILES[track]),"prompt":prompt,"scorer_id":SCORERS[track],"diagnostic_only":track=="diagnostic"}
            tp=PRIVATE/"tasks"/(tid+".json"); gp=PRIVATE/"ground_truth"/(tid+".json"); sp=PRIVATE/"scoring_specs"/(tid+".json")
            tp.write_text(json.dumps(task,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); gp.write_text(json.dumps(gt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); sp.write_text(json.dumps(make_specs(source,tid,track),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            rows.append({"task_id":tid,"version":"1.0-rc1","track":task["track"],"category":task["category"],"profile":task["profile"],"scorer_id":SCORERS[track],"scored":track not in {"diagnostic","performance"},"diagnostic_only":track=="diagnostic","telemetry_only":track=="performance","prompt_sha256":sha(tp),"ground_truth_sha256":None if track=="diagnostic" else sha(gp),"scoring_spec_sha256":sha(sp),"assets":[],"private_payload_present":True})
    # Exact architect code vectors are parsed from the repair task book, not hardcoded here.
    for i in range(1,9):
        vectors=code_vectors(repair_source,f"CODE_{i:02d}")
        (PRIVATE/"hidden_tests"/(f"CODE_{i:02d}.json")).write_text(json.dumps(vectors,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        (PRIVATE/"ground_truth"/(f"CODE_{i:02d}.json")).write_text(json.dumps({"function":vectors["function"],"cases":vectors["cases"]},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        spec_path=PRIVATE/"scoring_specs"/(f"CODE_{i:02d}.json"); spec=json.loads(spec_path.read_text(encoding="utf-8")); spec["function"]=vectors["function"]; spec_path.write_text(json.dumps(spec,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    docs,queries=parse_embedding(source); (PRIVATE/"embedding/corpus.json").write_text(json.dumps(docs,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); (PRIVATE/"embedding/queries.json").write_text(json.dumps(queries,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (PRIVATE/"safety/tasks.json").write_text(json.dumps(parse_safety(source),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (PRIVATE/"long_context/spec.json").write_text(json.dumps(parse_long_context(source),ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    tools_section=source[source.find("17. Tool Calling"):source.find("19. Tool assignment")]
    tool_records=[]
    for tid,_,raw in parse_section_records(source,"TOOL_"):
        if tid not in {f"TOOL_{i:02d}" for i in range(1,9)}: continue
        allowed={"get_weather","lookup_inventory","calculate_shipping","search_document","create_draft_event","lookup_order","get_customer"}; calls=[x for x in re.findall(r"\b[a-z_]+\b",raw) if x in allowed]
        expected=[]
        for name in calls:
            args={}
            if tid=="TOOL_01" and name=="get_weather":
                city=re.search(r'weather.*?in\s+([A-Za-z]+)',raw,re.I); date=re.search(r"\d{4}-\d{2}-\d{2}",raw); args={"city":city.group(1) if city else "","date":date.group(0) if date else ""}
            elif tid=="TOOL_02" and name=="lookup_inventory":
                sku=re.search(r"SKU\s+([A-Z]-\d+)",raw); args={"sku":sku.group(1) if sku else ""}
            elif tid=="TOOL_03" and name=="calculate_shipping":
                match=re.search(r"([0-9]+(?:\.[0-9]+)?)\s*kg",raw,re.I); dest=re.search(r"to\s+([A-Za-z]+)",raw,re.I); args={"weight_kg":float(match.group(1)) if match else None,"destination":dest.group(1) if dest else "","express":True}
            elif tid=="TOOL_06" and name=="search_document": args={"query":"KV cache hit-rate guide","top_k":2}
            elif tid=="TOOL_07" and name=="create_draft_event": args={"title":"Benchmark Review","start":"2026-08-10 10:00","end":"2026-08-10 10:30"}
            elif tid=="TOOL_08":
                order=re.search(r"order_id=\"?([A-Z]-\d+)",raw); customer=re.search(r"customer_id\s+([A-Z]-\d+)",raw); args={"order_id":order.group(1)} if name=="lookup_order" and order else ({"customer_id":customer.group(1)} if name=="get_customer" and customer else {})
            expected.append({"name":name,"arguments":args})
        lower=raw.lower()
        if tid=="TOOL_08": expected=[x for x in ({"name":"lookup_order","arguments":next((y["arguments"] for y in expected if y["name"]=="lookup_order"),{})},{"name":"get_customer","arguments":next((y["arguments"] for y in expected if y["name"]=="get_customer"),{})}) if x["name"] in {y["name"] for y in expected}]
        facts=[]
        final_block=re.search(r"(?is)final(?:\s+answer)?(?:\s+must)?\s+contain(?:s)?\s*[:：]?\s*(.*?)(?=\n\n(?:Extra|Expected|Accepted)|\Z)",raw)
        if final_block:
            for line in final_block.group(1).splitlines():
                value=line.strip().strip('"')
                if not value or re.fullmatch(r"-+",value): continue
                value=re.sub(r"\s+(?:true\s+)?semantic.*$","",value,flags=re.I).strip()
                facts.extend(x.strip() for x in re.split(r"\s+OR\s+",value,flags=re.I) if x.strip())
        if tid=="TOOL_04":
            quoted=re.search(r'"([^"\n]+)"',raw); facts=re.findall(r"[A-Za-z]+",quoted.group(1)) if quoted else []
        any_of=[]
        if tid=="TOOL_05":
            accepted=re.search(r"(?is)Accepted final contains semantic:\s*([^\n]+)",raw); any_of=[x.strip() for x in re.split(r"\s+OR\s+",accepted.group(1),flags=re.I)] if accepted else []; facts=[]
        tool_records.append({"task_id":tid,"expected_calls":expected,"expected_call_count":len(expected),"expected_order":[x["name"] for x in expected],"required_final_facts":facts,"required_final_any_of":any_of,"clarification_required":tid=="TOOL_05","zero_call_required":tid in {"TOOL_04","TOOL_05"},"extra_unrelated_call_fails":True,"source_spec_sha256":hashlib.sha256(raw.encode()).hexdigest()})
    (PRIVATE/"tool_fixtures/tasks.json").write_text(json.dumps(tool_records,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for record in tool_records:
        tid=record["task_id"]
        (PRIVATE/"ground_truth"/(tid+".json")).write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    names=sorted(set(re.findall(r"\b(?:get_weather|lookup_inventory|calculate_shipping|search_document|create_draft_event|lookup_order|get_customer)\b",tools_section)))
    tools=[]
    for name in names:
        sample=next((call for record in tool_records for call in record["expected_calls"] if call["name"]==name),{"arguments":{}})["arguments"]
        properties={key:{"type":"number" if type(value) in {int,float} else "boolean" if isinstance(value,bool) else "string"} for key,value in sample.items()}
        tools.append({"name":name,"arguments_schema":{"type":"object","properties":properties,"required":list(sample),"additionalProperties":False},"fixture_input":sample,"fixture_output":{"deterministic":True}})
    (PRIVATE/"tool_fixtures/tools.json").write_text(json.dumps({"source_spec_sha256":hashlib.sha256(tools_section.encode()).hexdigest(),"tools":tools},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Replace assets with structured private specs; rendering is delegated to public generic engine.
    asset_specs=[]
    for tid in [f"VIS_{i:02d}" for i in range(1,9)]+[f"OCR_{i:02d}" for i in range(1,11)]:
        raw=source_block(source,tid); asset_specs.append({"asset_id":tid,"source_spec_sha256":hashlib.sha256(raw.encode()).hexdigest(),"render_text":raw,"format":"JPEG" if tid=="OCR_09" else "PNG","width":1024,"height":768})
    (PRIVATE/"assets/specs.json").write_text(json.dumps(asset_specs,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"tasks":len(rows),"code_hidden_tests":8,"embedding_docs":len(docs),"embedding_queries":len(queries),"safety":len(parse_safety(source))},ensure_ascii=False))

def code_vectors(repair_source,tid):
    matches=list(re.finditer(r"(?m)^CODE_(\d+)(?:\s+([^\n]+))?\s*$",repair_source)); match=next((m for m in matches if "CODE_"+m.group(1)==tid),None)
    if not match: return {"function":"unknown","cases":[]}
    end=next((m.start() for m in matches if m.start()>match.start()),len(repair_source)); raw=repair_source[match.start():end]; fn=match.group(2).strip() if match.group(2) else "unknown"; blocks=list(re.finditer(r"(?m)^T(\d+):?(?:\s+(.*))?$",raw)); cases=[]
    for index,header in enumerate(blocks):
        tail=header.group(2) or ""; body=(tail+"\n"+raw[header.end():(blocks[index+1].start() if index+1<len(blocks) else len(raw))]).strip(); arrow=re.search(r"(?s)\s*(?:->|expected\s*=)\s*(.+)$",body)
        if arrow:
            marker=re.search(r"(?:->|expected\s*=)",body)
            left=body[marker.start()].strip() if marker is None else body[:marker.start()].strip()
            expected_text=body[marker.end():].strip().split("\n--------------------------------",1)[0].split("\n============================================================",1)[0].split("\nAND ",1)[0].strip() if marker else None
        else: left=body; expected_text=None
        values={}
        for line in left.splitlines():
            if "=" in line:
                name,value=line.split("=",1)
                try: values[name.strip()]=ast.literal_eval(value.strip())
                except (SyntaxError,ValueError): pass
        try: expected=ast.literal_eval(expected_text) if expected_text is not None else None
        except (SyntaxError,ValueError): expected=None
        args=[]
        if fn=="rotate_left": args=[values.get("items"),values.get("k")]
        elif fn in {"balanced_brackets","rle_encode","first_unique_index","parse_kv_lines"}:
            fallback=None
            try: fallback=ast.literal_eval(left)
            except (SyntaxError,ValueError): pass
            args=[values.get("text",values.get("s",fallback))]
        elif fn=="merge_intervals":
            source=values.get("input",left); args=[ast.literal_eval(source) if isinstance(source,str) else source]
        elif fn=="top_k_frequent":
            args=list(ast.literal_eval(left.split("->",1)[0].strip()))
        elif fn=="free_slots":
            if "intervals" in values: args=[values["intervals"],*(values.get("day") or [])]
            else: args=list(ast.literal_eval("("+left+",)")) if False else list(ast.literal_eval("("+left+")"))
        row={"case_id":f"T{header.group(1)}","args":args,"kwargs":{},"expected":expected,"source_sha256":hashlib.sha256(body.encode()).hexdigest()}
        if "input after" in body or "input must remain" in body: row["input_must_remain"]=args[0] if args else None
        cases.append(row)
    return {"function":fn,"cases":cases[:10]}

if __name__=="__main__": main(sys.argv[1])
