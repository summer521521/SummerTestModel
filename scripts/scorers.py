"""Offline deterministic scorer primitives. Expected values are loaded externally."""
from __future__ import annotations
import json, math, re
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

def numeric(actual: str, expected: float, tolerance=1e-6) -> dict:
    values=re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?%?", actual)
    numbers=[]
    for value in values:
        numbers.append(float(value[:-1])/100 if value.endswith("%") else float(value))
    if len(set(numbers)) > 1: return {"status":"invalid_answer","score":0.0}
    return {"status":"scored","score":1.0 if numbers and math.isclose(numbers[-1], expected, abs_tol=tolerance) else 0.0}

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

def cer(actual: str, expected: str) -> float:
    if not expected: return 0.0 if actual else 1.0
    return 1.0 - SequenceMatcher(None, actual, expected).ratio()

def ocr_score(actual: str, expected: str) -> dict:
    repetition=len(actual)>3*max(1,len(expected)) and bool(re.search(r"(.{3,})\1", actual))
    error=cer(actual, expected)
    return {"cer":error,"semantic_score":max(0.0,1.0-error),"repetition_degeneration":repetition,"completion_status":"completed" if actual.strip() else "empty"}

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
