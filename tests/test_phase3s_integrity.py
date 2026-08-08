import json
import copy
import unittest
from pathlib import Path
from scripts.phase3r_validator import validate
from scripts.scorers import classification_metrics, score_task, tool_trace_validator, parse_safety

ROOT=Path(__file__).resolve().parents[1]

class Phase3SIntegrityTests(unittest.TestCase):
    def test_scorer_ids_are_referential(self):
        tasks=json.loads((ROOT/"config/task_manifest.rc1.public.json").read_text(encoding="utf-8"))["tasks"]
        scorers=json.loads((ROOT/"config/scorer_manifest.rc1.public.json").read_text(encoding="utf-8"))["scorers"]
        by={x["scorer_id"]:x for x in scorers}
        self.assertTrue(all(t["scorer_id"] in by for t in tasks))
        self.assertTrue(all(t["track"]==by[t["scorer_id"]]["track"] or t["track"]=="diagnostic" for t in tasks))

    def test_code_vectors_are_structured(self):
        for path in sorted((ROOT/"private_benchmark/1.0-rc1/hidden_tests").glob("CODE_*.json")):
            data=json.loads(path.read_text(encoding="utf-8")); self.assertEqual(len(data["cases"]),10)
            self.assertTrue(all(isinstance(c.get("args"),list) and isinstance(c.get("kwargs"),dict) and "expected" in c for c in data["cases"]))

    def test_golden_gate(self):
        data=json.loads((ROOT/"handoff/scorer_golden_validation.json").read_text(encoding="utf-8"))
        self.assertEqual(data["tasks_checked"],116); self.assertEqual(data["code_cases_checked"],80); self.assertEqual(data["full_score_pass"],data["tasks_checked"]); self.assertFalse(data["failures"]); self.assertFalse(data["wrong_fixture_failures"])

    def test_referential_mismatch_fails_validator(self):
        import tempfile, shutil
        with tempfile.TemporaryDirectory() as td:
            target=Path(td); shutil.copytree(ROOT/"config",target/"config"); shutil.copytree(ROOT/"private_benchmark/1.0-rc1",target/"private_benchmark/1.0-rc1")
            manifest=json.loads((target/"config/task_manifest.rc1.public.json").read_text(encoding="utf-8")); manifest["tasks"][0]["scorer_id"]="missing_scorer"
            (target/"config/task_manifest.rc1.public.json").write_text(json.dumps(manifest),encoding="utf-8")
            result=validate(target); self.assertFalse(result["valid"]); self.assertGreater(result["metrics"]["scorer_referential_errors"],0)

    def test_core_partial_and_reasoning_split(self):
        spec={"type":"deterministic_core"}; result=score_task({"final_answer":"path = A-C-B-D-E"},{"task_id":"CORE_LOGIC_04"},{"value":"path = A-C-B-D-E\ncost = 10"},spec); self.assertEqual(result["task_score"],.6)
        spec={"type":"deterministic_reasoning"}; result=score_task({"final_answer":"Ana=Y\nBo=X\nCy=Z\ntotal=8"},{"task_id":"RSN_09"},{"value":"Ana=Y\nBo=X\nCy=Z\ntotal=9"},spec); self.assertAlmostEqual(result["task_score"],.7)

    def test_tool_zero_clarification_and_chain(self):
        zero={"expected_calls":[],"zero_call_required":True,"clarification_required":False,"required_final_facts":[]}; self.assertEqual(tool_trace_validator({"tool_calls":[],"final_answer":"ok"},zero)["exact_task_success"],1)
        clarify={**zero,"clarification_required":True,"required_final_facts":["city"]}; self.assertEqual(tool_trace_validator({"tool_calls":[],"clarification":True,"final_answer":"Which city?"},clarify)["exact_task_success"],1)
        chain={"expected_calls":[{"name":"a","arguments":{"id":"1"}},{"name":"b","arguments":{"id":"2"}}],"required_final_facts":["done"]}; actual={"tool_calls":copy.deepcopy(chain["expected_calls"]),"final_answer":"done"}; self.assertEqual(tool_trace_validator(actual,chain)["multi_step_success"],1)

    def test_frozen_tool_fixtures(self):
        fixtures={x["task_id"]:x for x in json.loads((ROOT/"private_benchmark/1.0-rc1/tool_fixtures/tasks.json").read_text(encoding="utf-8"))}
        for tid in ("TOOL_04","TOOL_05","TOOL_08"):
            expected=fixtures[tid]; facts=list(expected["required_final_facts"])+(expected.get("required_final_any_of") or [])[:1]
            actual={"tool_calls":copy.deepcopy(expected["expected_calls"]),"final_answer":" ".join(facts),"clarification":expected["clarification_required"]}
            self.assertEqual(tool_trace_validator(actual,expected)["exact_task_success"],1)
        shipping=fixtures["TOOL_03"]; wrong=copy.deepcopy(shipping["expected_calls"]); key=next(k for k,v in wrong[0]["arguments"].items() if isinstance(v,float)); wrong[0]["arguments"][key]=str(wrong[0]["arguments"][key])
        self.assertEqual(tool_trace_validator({"tool_calls":wrong},shipping)["exact_task_success"],0)

    def test_native_safety_parsers(self):
        self.assertEqual(parse_safety("comment yes","shieldgemma:2b"),None)
        self.assertEqual(parse_safety("prose yes\n<score>no</score>","granite guardian"),0)
        metrics=classification_metrics([0]*10+[1]*10,[0]*10+[1]*10); self.assertEqual(metrics["accuracy"],1.0); self.assertEqual(metrics["f1"],1.0)

    def test_long_context_and_assignment_filters(self):
        meta=json.loads((ROOT/"private_benchmark/1.0-rc1/long_context/metadata.json").read_text(encoding="utf-8")); self.assertTrue(all(4000<=x["whitespace_token_count"]<=22000 and x["target_occurrences"]==1 for x in meta)); self.assertAlmostEqual(next(x["target_position_fraction"] for x in meta if x["task_id"]=="CTX32_02"),.90,delta=.03)
        plan=json.loads((ROOT/"config/model_execution_plan.rc1.public.json").read_text(encoding="utf-8")); models={x["model"]:x for x in plan["models"]}; self.assertFalse(any(x.startswith("CTX") for x in models["gemma3n:e4b"]["task_ids"])); self.assertFalse(any(x.startswith("CTX32") for x in models["smollm2:1.7b"]["task_ids"]))

    def test_performance_is_telemetry_only(self):
        task=next(x for x in json.loads((ROOT/"config/task_manifest.rc1.public.json").read_text(encoding="utf-8"))["tasks"] if x["task_id"]=="PERF_01")
        self.assertFalse(task["scored"]); self.assertTrue(task["telemetry_only"])

    def test_translation_weights_and_assets(self):
        for p in sorted((ROOT/"private_benchmark/1.0-rc1/scoring_specs").glob("TRANS_*.json")): self.assertEqual(json.loads(p.read_text(encoding="utf-8"))["weight_sum"],10)
        metadata={x["asset_id"]:x for x in json.loads((ROOT/"private_benchmark/1.0-rc1/assets/metadata.json").read_text(encoding="utf-8"))}; self.assertIn("column_labels_A_to_D",metadata["VIS_05"]["content_features"]); self.assertFalse(metadata["VIS_08"]["source_block_rendered"]); self.assertTrue(all(metadata[f"OCR_{i:02d}"]["non_empty_bounding_box"] for i in range(1,11))); self.assertEqual(metadata["OCR_09"]["format"],"JPEG")

    def test_translation_matchers_and_embedding_cosine(self):
        spec={"type":"translation_checklist","components":[{"id":"identifier","weight":3,"matcher_type":"regex","accepted_patterns":[r"ID-7"],"forbidden_patterns":[]},{"id":"negation","weight":3,"matcher_type":"regex","accepted_patterns":[r"do\s+not\s+delete"],"forbidden_patterns":[]},{"id":"number","weight":4,"matcher_type":"regex","accepted_patterns":[r"14\s*ms"],"forbidden_patterns":[]}]}
        full=score_task({"final_answer":"ID-7 do not delete 14 ms"},{},{},spec); corrupt=score_task({"final_answer":"ID-8 delete 41 ms"},{},{},spec); self.assertEqual(full["normalized_score_0_to_1"],1.0); self.assertLess(corrupt["normalized_score_0_to_1"],1.0)
        retrieval=score_task({"corpus_embeddings":{"D1":[1,0],"D2":[0,1]},"query_embedding":[1,0]},{},{"relevant_doc_ids":["D1"]},{"type":"embedding_retrieval"}); self.assertEqual(retrieval["recall_at_1"],1.0); self.assertEqual(retrieval["mrr"],1.0)

if __name__=="__main__": unittest.main()
