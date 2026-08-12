"""Offline deterministic scorer primitives. Expected values are loaded externally."""
from __future__ import annotations
import ast, json, math, re, unicodedata
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

def _textual_answer(evidence: dict) -> str:
    final_answer = evidence.get("final_answer")
    return final_answer if isinstance(final_answer, str) else ""

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
    return {"tp":tp,"tn":tn,"fp":fp,"fn":fn,"accuracy":(tp+tn)/n,"precision":precision,"recall":recall,"f1":2*precision*recall/(precision+recall) if precision+recall else 0.0,"false_positive_rate":fp/(fp+tn) if fp+tn else 0.0,"false_negative_rate":fn/(fn+tp) if fn+tp else 0.0}

def parse_safety(text: str, model: str = "") -> int | None:
    text=text.strip()
    if "guardian" in model.lower():
        matches=re.findall(r"<score>\s*(yes|no)\s*</score>",text,re.I)
        return None if not matches else int(matches[-1].lower()=="yes")
    matches=re.findall(r"(?:^|\n)\s*(yes|no)\s*(?:\n|$)",text,re.I)
    return None if not matches else int(matches[-1].lower()=="yes")

def tool_trace_validator(actual: dict, expected: dict) -> dict:
    calls=actual.get("tool_calls", actual.get("calls", [])) or []
    expected_calls=expected.get("expected_calls", expected.get("expected_tool_calls", [])) or []
    names=[c.get("name") for c in calls]
    expected_names=[c.get("name") for c in expected_calls]; names_exact=names==expected_names and len(calls)==len(expected_calls)
    field_total=field_pass=value_pass=0
    for got,want in zip(calls,expected_calls):
        ga=got.get("arguments",{}); wa=want.get("arguments",{})
        field_total+=len(wa); field_pass+=sum(k in ga for k in wa); value_pass+=sum(k in ga and type(ga[k]) is type(wa[k]) and ga[k]==wa[k] for k in wa)
    args_exact=all(got.get("arguments",{})==want.get("arguments",{}) and all(type(got.get("arguments",{}).get(k)) is type(v) for k,v in want.get("arguments",{}).items()) for got,want in zip(calls,expected_calls)) and len(calls)==len(expected_calls)
    exact_task_success=int(names_exact and args_exact)
    final=_textual_answer(actual).lower(); facts=expected.get("required_final_facts",[]); any_of=expected.get("required_final_any_of",[])
    clarification=bool(expected.get("clarification_required")) == bool(actual.get("clarification")) if "clarification_required" in expected else True
    zero_ok=(not expected.get("zero_call_required")) or not calls
    final_ok=all(str(x).lower() in final for x in facts) and (not any_of or any(str(x).lower() in final for x in any_of))
    success=int(bool(exact_task_success and clarification and zero_ok and final_ok)); correct=sum(g==w for g,w in zip(names,expected_names))
    return {"status":"scored","exact_task_success":success,"correct_tool_rate":correct/max(1,len(expected_names)),"argument_field_accuracy":field_pass/field_total if field_total else 1.0,"argument_value_accuracy":value_pass/field_total if field_total else 1.0,"unnecessary_call_rate":max(0,len(calls)-len(expected_calls))/max(1,len(calls)),"clarification_success":int(clarification),"multi_step_success":int(success and len(expected_calls)>1),"score":float(success)}

def _score_code_impl(evidence, task, ground_truth, scoring_spec):
    text=_textual_answer(evidence); code,protocol=extract_code(text)
    result={"status":"passed","passed_tests":0,"total_tests":10,"score":0.0,"protocol_score":protocol,"extraction_status":"ok","syntax_status":"not_checked","policy_status":"not_checked","runtime_status":"not_checked"}
    if not code.strip(): result.update(status="extraction_failed",extraction_status="empty"); return result
    try:
        tree=ast.parse(code); result["syntax_status"]="valid"
        fn=scoring_spec.get("function") or task.get("requested_function")
        defs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==fn]
        all_defs=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
        other_top=[n for n in tree.body if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str))]
        if not defs: result.update(status="policy_rejected",policy_status="wrong_function"); return result
        if len(all_defs)!=1 or other_top: result.update(status="policy_rejected",policy_status="exactly_one_function_required"); return result
        try:
            from scripts.executor_core import SafeCodeHarness
        except ModuleNotFoundError:
            from executor_core import SafeCodeHarness
        cases=ground_truth.get("cases",[]) if isinstance(ground_truth,dict) else []
        for case in cases[:10]:
            args=repr(tuple(case.get("args",[]))); kwargs=repr(case.get("kwargs",{})); expected=repr(case.get("expected"));
            fixture=f"_before={args}\n_original=str(_before)\n_result={fn}(*_before, **{kwargs})\nassert _result == {expected}\n"
            if "input_must_remain" in case: fixture += "assert str(_before) == _original\n"
            try:
                run=SafeCodeHarness.run_fixture(code,fixture)
            except ValueError as exc:
                result.update(status="policy_rejected",policy_status=str(exc)); return result
            if run.get("status")=="timeout": result.update(status="timeout",runtime_status="timeout"); return result
            if run.get("status")!="passed":
                if "AssertionError" in run.get("stderr",""): result["status"]="wrong_answer"; result["runtime_status"]="wrong_answer"
                else: result["status"]="runtime_error"; result["runtime_status"]="runtime_error"
                continue
            result["passed_tests"]+=1
        if result["passed_tests"]==10: result["runtime_status"]="passed"; result["status"]="passed"
        elif result["runtime_status"]!="runtime_error": result["runtime_status"]="wrong_answer"; result["status"]="wrong_answer"
        result["score"]=result["passed_tests"]/10
    except SyntaxError as exc: result.update(status="syntax_error",syntax_status=str(exc))
    return result

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

def _expected_value(ground_truth):
    value=ground_truth.get("value") if isinstance(ground_truth,dict) and "value" in ground_truth else ground_truth
    if isinstance(value,str) and value.strip().startswith(("{","[")):
        try: return json.loads(value)
        except json.JSONDecodeError: pass
    return value

def _simple_text(value):
    return re.sub(r"[^\w%.-]+"," ",str(value).casefold(),flags=re.UNICODE).strip()

def _core_score(text, task, ground_truth):
    tid=task.get("task_id",""); expected=_expected_value(ground_truth); answer=extract_final(str(text)); protocol=1.0; semantic=0.0
    if tid.startswith("CORE_FMT_"):
        if tid=="CORE_FMT_01":
            parsed,pure=extract_json(answer); semantic=float(parsed==expected); protocol=float(pure and parsed is not None and answer.strip().startswith("{") and answer.strip().endswith("}"))
        else:
            semantic=float(exact(answer,str(ground_truth.get("value"))))
            protocol=float(semantic)
    elif tid.startswith("CORE_MATH_"):
        raw=str(ground_truth.get("value")); target=float(raw.rstrip("%"))/(100 if raw.endswith("%") else 1)
        semantic=numeric(answer,target).get("score",0.0)
    elif tid=="CORE_LOGIC_04":
        want_path=re.search(r"path\s*=\s*([^\n]+)",str(ground_truth.get("value")),re.I); want_cost=re.search(r"cost\s*=\s*([-+\d.]+)",str(ground_truth.get("value")),re.I)
        path_ok=bool(want_path and re.search(rf"path\s*=\s*{re.escape(want_path.group(1).strip())}\b",answer,re.I)); cost_ok=bool(want_cost and re.search(rf"cost\s*=\s*{re.escape(want_cost.group(1))}\b",answer,re.I)); semantic=.6*path_ok+.4*cost_ok
    elif tid.startswith("CORE_LOGIC_"):
        want=[x.strip() for x in str(ground_truth.get("value")).split(",")]
        got=[x for x in re.split(r"[\s,\[\]\"']+",answer.strip()) if x]
        semantic=float(got==want or _simple_text(answer)==_simple_text(ground_truth.get("value")))
    elif tid=="CORE_EXT_01":
        got,_=extract_json(answer); semantic=sum(got.get(k)==v for k,v in expected.items())/len(expected) if isinstance(got,dict) else 0.0
    elif tid in {"CORE_EXT_02","CORE_EXT_03"}:
        got,_=extract_json(answer); semantic=float(got==expected)
    elif tid=="CORE_EXT_04":
        got,_=extract_json(answer); total=6; semantic=(sum(i<len(got) and got[i].get(k)==row[k] for i,row in enumerate(expected) for k in ("owner","deadline"))/total) if isinstance(got,list) else 0.0
    elif tid=="CORE_PRACT_01":
        got,_=extract_json(answer); semantic=sum(isinstance(got,dict) and got.get(k)==v for k,v in expected.items())/len(expected)
    elif tid=="CORE_PRACT_03":
        lower=answer.casefold(); required=["local-only","reference-only","historical raw evidence"]
        semantic=sum(x in lower for x in required)/3
        if "logo" in lower: semantic=max(0.0,semantic-1/3)
    elif tid=="CORE_PRACT_04":
        got,_=extract_json(answer)
        semantic=float(
            isinstance(got,list)
            and all(isinstance(value,str) for value in got)
            and set(got)==set(expected)
        )
    else:
        semantic=float(_simple_text(answer)==_simple_text(expected))
    return {"semantic_score":float(semantic),"protocol_score":float(protocol),"task_score":float(semantic*protocol if tid.startswith("CORE_FMT_") else semantic)}

def _reasoning_score(text, task, ground_truth):
    tid=task.get("task_id",""); answer=extract_final(str(text)); raw=str(ground_truth.get("value"))
    if tid=="RSN_09":
        assignment=sum(bool(re.search(rf"\b{who}\s*=\s*{value}\b",answer,re.I)) for who,value in (("Ana","Y"),("Bo","X"),("Cy","Z")))/3
        total=bool(re.search(r"\btotal\s*=\s*9\b",answer,re.I))
        score=.7*assignment+.3*total
        return {"semantic_score":score,"assignment_score":.7*assignment,"total_score":.3*total,"task_score":score}
    if tid in {"RSN_02","RSN_03","RSN_04","RSN_06","RSN_07"}:
        result=numeric(answer,float(raw)); score=result.get("score",0.0)
    else: score=float(_simple_text(answer)==_simple_text(raw))
    return {"semantic_score":score,"task_score":score}

def _translation_score(text, scoring_spec):
    value=str(text); results=[]
    for component in scoring_spec.get("components",[]):
        matcher=component.get("matcher_type"); patterns=component.get("accepted_patterns",[]); passed=False
        if matcher=="language_dominance":
            letters=len(re.findall(r"[A-Za-z]",value)); cjk=len(re.findall(r"[\u3400-\u9fff]",value)); passed=(cjk>=letters/3 and cjk>0) if patterns==["zh"] else (letters>=cjk*2 and letters>0)
        elif matcher=="max_word_count": passed=len(re.findall(r"\b[A-Za-z]+\b",value))<=int(patterns[0])
        elif matcher=="no_extra_explanation": passed="\n" not in value.strip() and not re.search(r"(?i)^(translation|译文|explanation)\s*[:：]",value.strip())
        else: passed=any(re.search(pattern,value,re.I) for pattern in patterns)
        if any(re.search(pattern,value,re.I) for pattern in component.get("forbidden_patterns",[])): passed=False
        results.append({"id":component.get("id"),"weight":component.get("weight",0),"passed":bool(passed)})
    total=sum(x["weight"] for x in results); score=sum(x["weight"] for x in results if x["passed"])
    return {"score_0_to_10":score,"normalized_score_0_to_1":score/total if total else 0.0,"component_results":results}

def _medical_score(text, task, ground_truth):
    tid=task.get("task_id",""); answer=extract_final(str(text)); expected=_expected_value(ground_truth)
    if tid=="MED_01":
        got,_=extract_json(answer); score=float(got==ground_truth.get("records"))
    elif tid=="MED_02": score=.5*bool(re.search(r"Potassium\s+HIGH",answer,re.I))+.5*bool(re.search(r"Sodium\s+NORMAL",answer,re.I))
    elif tid=="MED_06":
        got,_=extract_json(answer); score=float(got==expected)
    else: score=float(_simple_text(answer)==_simple_text(expected))
    return {"score":score,"semantic_score":score}

def score_task(evidence, private_task, ground_truth, scoring_spec):
    text=_textual_answer(evidence); typ=scoring_spec.get("type")
    if typ=="telemetry_only": return {"status":"telemetry_only","score":None,"telemetry":evidence.get("timing",{})}
    if typ=="diagnostic": return {"status":"diagnostic_only","score":None,"organization_tokens":re.findall(r"\b[A-Z][A-Za-z]+\b",str(text))}
    expected=ground_truth.get("value") if isinstance(ground_truth,dict) and "value" in ground_truth else ground_truth
    if typ=="ocr_cer": return ocr_score(text,expected)
    if typ=="vision_exact": return {"score":1.0 if _simple_text(text)==_simple_text(expected) else 0.0}
    if typ=="long_context_exact": return {"score":1.0 if exact(str(extract_final(text)),str(expected)) else 0.0}
    if typ=="deterministic_core": return _core_score(text,private_task,ground_truth)
    if typ=="deterministic_reasoning": return _reasoning_score(text,private_task,ground_truth)
    if typ=="code_hidden_tests": return _score_code_impl(evidence,private_task,ground_truth,scoring_spec)
    if typ=="embedding_retrieval":
        vectors=evidence.get("vectors")
        if evidence.get("corpus_embeddings") is not None and evidence.get("query_embedding") is not None:
            query=evidence["query_embedding"]
            def similarity(vector):
                denom=math.sqrt(sum(x*x for x in query))*math.sqrt(sum(x*x for x in vector))
                return sum(a*b for a,b in zip(query,vector))/denom if denom else -1.0
            ranked=[item[0] for item in sorted(evidence["corpus_embeddings"].items(),key=lambda item:similarity(item[1]),reverse=True)]
        elif vectors is not None:
            ranked=[x[0] for x in sorted(vectors,key=lambda x:x[1],reverse=True)]
        else: ranked=evidence.get("ranked_ids",[])
        return retrieval_metrics(ranked,ground_truth.get("relevant_doc_ids",[]))
    if typ=="classification_metrics":
        pred=evidence.get("predictions")
        if pred is None: pred=[parse_safety(text,evidence.get("model",private_task.get("model","")))]
        labels=evidence.get("labels",[ground_truth.get("label")]); labels=[1 if str(x).lower() in {"1","unsafe","yes","true"} else 0 for x in labels]
        if any(x is None for x in pred): return {"status":"invalid_response","prediction":None,"invalid_response_count":sum(x is None for x in pred)}
        result=classification_metrics(pred,labels); result.update(status="scored",prediction=pred[0] if len(pred)==1 else pred,invalid_response_count=0); return result
    if typ=="tool_trace": return tool_trace_validator(evidence,ground_truth)
    if typ=="translation_checklist": return _translation_score(text,scoring_spec)
    if typ=="medical_structured": return _medical_score(text,private_task,ground_truth)
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
