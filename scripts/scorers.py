"""Offline deterministic scorer primitives. Expected values are loaded externally."""
from __future__ import annotations
import json, math, re, unicodedata
from pathlib import Path
from difflib import SequenceMatcher

def load_private_expected(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")

def exact(actual: str, expected: str, normalize_newline=True) -> bool:
    a, e = actual.strip(), expected.strip()
    if normalize_newline: a, e = a.replace("\r\n","\n"), e.replace("\r\n","\n")
    return a == e

def extract_json(text: str):
    value=text.strip(); protocol=not value.startswith("```") and not value.endswith("```")
    if value.startswith("```"):
        value=re.sub(r"^```(?:json)?\s*|\s*```$", "", value, flags=re.I|re.S).strip()
    try: return json.loads(value), protocol
    except json.JSONDecodeError: return None, protocol

def json_fields(actual: str, expected: dict) -> dict:
    parsed, protocol=extract_json(actual)
    return {"semantic_score": 1.0 if parsed == expected else 0.0, "protocol_score": 1.0 if protocol and parsed is not None else 0.0, "parsed": parsed}

def _numeric_values(text):
    return [float(x[:-1])/100 if x.endswith("%") else float(x) for x in re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?%?", text)]

def numeric(actual: str, expected: float, tolerance=1e-6, accepted_values=None) -> dict:
    final_lines=re.findall(r"(?im)^\s*FINAL\s*:\s*(.*?)\s*$",actual)
    line=final_lines[-1] if final_lines else next((x for x in reversed(actual.splitlines()) if _numeric_values(x)),actual)
    values=_numeric_values(line)
    if len(set(values)) > 1: return {"status":"invalid_answer","score":0.0}
    accepted=accepted_values or [expected]
    return {"status":"scored","score":1.0 if values and any(math.isclose(values[0], float(x), abs_tol=tolerance) for x in accepted) else 0.0}

def ordered_sequence(actual, expected) -> bool:
    if isinstance(actual, str): actual=[x.strip() for x in actual.split(",")]
    return list(actual)==list(expected)

def set_score(actual, expected) -> float:
    return 1.0 if set(actual)==set(expected) else 0.0

def checklist(actual: str, checks: dict[str, bool]) -> dict:
    lower=actual.lower(); passed=sum(bool(ok and key.lower() in lower) for key,ok in checks.items())
    return {"passed":passed,"total":len(checks),"score":passed/len(checks) if checks else 0.0}

def extract_final(text: str) -> str:
    matches=re.findall(r"(?im)^\s*FINAL\s*:\s*(.+?)\s*$", text)
    return matches[-1].strip() if matches else text.strip()

def levenshtein(actual: str, expected: str) -> dict:
    a=list(unicodedata.normalize("NFC",actual.replace("\r\n","\n")).strip()); b=list(unicodedata.normalize("NFC",expected.replace("\r\n","\n")).strip())
    previous=list(range(len(b)+1)); rows=[previous]
    for i,x in enumerate(a,1):
        current=[i]
        for j,y in enumerate(b,1): current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(x!=y)))
        previous=current; rows.append(current)
    distance=previous[-1]; return {"edit_distance":distance,"cer":distance/len(b) if b else (0.0 if not a else float(distance)),"exact_match":a==b}

def cer(actual: str, expected: str) -> float: return levenshtein(actual,expected)["cer"]

def ocr_score(actual: str, expected: str) -> dict:
    normalized=levenshtein(actual,expected); repetition=len(actual)>3*max(1,len(expected)) and bool(re.search(r"(.{3,})\1", actual))
    error=normalized["cer"]
    return {**normalized,"char_accuracy":max(0.0,1.0-error),"semantic_score":max(0.0,1.0-error),"repetition_degeneration":repetition,"completion_status":"completed" if actual.strip() else "empty"}

def classification_metrics(predicted, expected) -> dict:
    tp=sum(p==e==1 for p,e in zip(predicted,expected)); tn=sum(p==e==0 for p,e in zip(predicted,expected)); fp=sum(p==1 and e==0 for p,e in zip(predicted,expected)); fn=sum(p==0 and e==1 for p,e in zip(predicted,expected)); n=max(1,len(expected))
    precision=tp/(tp+fp) if tp+fp else 0.0; recall=tp/(tp+fn) if tp+fn else 0.0
    return {"tp":tp,"tn":tn,"fp":fp,"fn":fn,"accuracy":(tp+tn)/n,"precision":precision,"recall":recall,"f1":2*precision*recall/(precision+recall) if precision+recall else 0.0}

def parse_safety(text: str) -> int | None:
    match=re.search(r"(?:<score>\s*)?(yes|no)(?:\s*</score>)?",text,re.I)
    return None if not match else int(match.group(1).lower()=="yes")

def tool_trace_validator(actual: dict, expected: dict) -> dict:
    ok=actual.get("name")==expected.get("name") and actual.get("arguments")==expected.get("arguments")
    return {"status":"scored","valid":ok,"score":1.0 if ok else 0.0}

def cosine_retrieval(vectors, relevant, k=1) -> dict:
    ranked=sorted(vectors, key=lambda x:x[1], reverse=True); top=[x[0] for x in ranked[:k]]
    return {"recall_at_k":float(bool(set(top)&set(relevant))),"mrr":next((1/(i+1) for i,x in enumerate(ranked) if x[0] in relevant),0.0)}

def retrieval_metrics(ranked_ids, relevant):
    relevant=set(relevant); ranks={x:i+1 for i,x in enumerate(ranked_ids)}; rr=next((1/ranks[x] for x in relevant if x in ranks),0.0)
    def recall(k): return float(bool(relevant.intersection(ranked_ids[:k])))
    dcg=sum(1/math.log2(i+2) for i,x in enumerate(ranked_ids[:5]) if x in relevant); ideal=sum(1/math.log2(i+2) for i in range(min(5,len(relevant))))
    return {"recall_at_1":recall(1),"recall_at_3":recall(3),"recall_at_5":recall(5),"mrr":rr,"ndcg_at_5":dcg/ideal if ideal else 0.0}

def extract_code(text):
    fenced=re.search(r"```(?:python)?\s*(.*?)```",text,re.I|re.S)
    return (fenced.group(1).strip(),0.0) if fenced else (text.strip(),1.0)

def score_task(evidence, private_task, ground_truth, scoring_spec):
    text=evidence.get("final_answer") or evidence.get("raw_response") or ""; typ=scoring_spec.get("type")
    if typ=="telemetry_only": return {"status":"telemetry_only","score":None,"telemetry":evidence.get("timing",{})}
    if typ=="diagnostic": return {"status":"diagnostic_only","score":None,"organization_tokens":re.findall(r"\b[A-Z][A-Za-z]+\b",str(text))}
    expected=ground_truth.get("value") if isinstance(ground_truth,dict) and "value" in ground_truth else ground_truth
    if typ in {"ocr_cer","vision_exact","long_context_exact"}: return ocr_score(text,expected) if typ=="ocr_cer" else {"score":1.0 if exact(str(text),str(expected)) else 0.0}
    if typ in {"deterministic_reasoning","deterministic_core"}:
        final=extract_final(str(text));
        if isinstance(expected,(int,float)): return numeric(final,expected)
        parsed,_=extract_json(final)
        return {"score":1.0 if (parsed==expected or exact(final,str(expected))) else 0.0,"protocol_score":1.0 if parsed is not None else 0.0}
    if typ=="code_hidden_tests": return {"status":"extraction_ready","code":extract_code(str(text))[0],"protocol_score":extract_code(str(text))[1]}
    if typ=="embedding_retrieval": return retrieval_metrics(evidence.get("ranked_ids",[]),ground_truth.get("relevant_doc_ids",[]))
    if typ=="classification_metrics": return classification_metrics(evidence.get("predictions",[]),evidence.get("labels",[]))
    if typ=="tool_trace": return tool_trace_validator(evidence.get("tool_call",{}),ground_truth.get("expected_tool_call",{}))
    if typ=="translation_checklist": return checklist(str(text),scoring_spec.get("checks",{}))
    return {"score":1.0 if exact(str(text),str(expected)) else 0.0}

def _dispatch(name,evidence,task,gt,spec): return score_task(evidence,task,gt,spec)
def score_core(evidence,task,gt,spec): return _dispatch("core",evidence,task,gt,spec)
def score_reasoning(evidence,task,gt,spec): return _dispatch("reasoning",evidence,task,gt,spec)
def score_code(evidence,task,gt,spec): return _dispatch("code",evidence,task,gt,spec)
def score_translation(evidence,task,gt,spec): return _dispatch("translation",evidence,task,gt,spec)
def score_tools(evidence,task,gt,spec): return _dispatch("tools",evidence,task,gt,spec)
def score_vision(evidence,task,gt,spec): return _dispatch("vision",evidence,task,gt,spec)
def score_ocr(evidence,task,gt,spec): return _dispatch("ocr",evidence,task,gt,spec)
def score_long_context(evidence,task,gt,spec): return _dispatch("long_context",evidence,task,gt,spec)
def score_embedding(evidence,task,gt,spec): return _dispatch("embedding",evidence,task,gt,spec)
def score_safety(evidence,task,gt,spec): return _dispatch("safety",evidence,task,gt,spec)
def score_medical(evidence,task,gt,spec): return _dispatch("medical",evidence,task,gt,spec)
def score_performance(evidence,task,gt,spec): return _dispatch("performance",evidence,task,gt,spec)
def score_diagnostic(evidence,task,gt,spec): return _dispatch("diagnostic",evidence,task,gt,spec)
