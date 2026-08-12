import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import rc1_runner
from scripts.executor_core import CircuitBreaker, CircuitConfig, EvidenceStore, Executor
from scripts.ollama_adapter import OllamaAdapter

ROOT=Path(__file__).resolve().parents[1]

class RC1RunnerIntegrationTests(unittest.TestCase):
    def test_item_builder_carries_images_and_embedding_corpus(self):
        bundle=rc1_runner.config_bundle(); builder=rc1_runner.RC1ItemBuilder(bundle)
        vision=next(x for x in builder.all_items(selected_model="qwen3.5:4b") if x["track"]=="vision")
        self.assertTrue(vision["images"]); self.assertEqual(vision["messages"][0]["images"],vision["images"])
        embedding=next(x for x in builder.all_items(selected_model="qwen3-embedding:latest") if x["track"]=="embedding")
        self.assertEqual(len(embedding["embedding_corpus"]),24); self.assertEqual(embedding["task_id"],"EMB_Q01")

    def test_guardian_runtime_override_sends_think_false_without_capability(self):
        bundle=rc1_runner.config_bundle(); item=next(x for x in rc1_runner.RC1ItemBuilder(bundle).all_items(selected_model="granite4.1-guardian:8b") if x["task_id"]=="SAFE01")
        item={**item,"capabilities":[]}
        captured={}
        chunks=iter([b'{"message":{"content":"<score> no </score>"},"done":true,"done_reason":"stop"}\n'])
        class Response:
            def readline(self):
                try:return next(chunks)
                except StopIteration:return b""
        def fake_urlopen(request, timeout):
            captured.update(json.loads(request.data.decode("utf-8"))); return Response()
        with mock.patch("scripts.ollama_adapter.urllib.request.urlopen",side_effect=fake_urlopen):
            result=OllamaAdapter(max_transport_retries=0).infer(item)
        self.assertIs(captured["think"],False); self.assertEqual(result["think_reason"],"explicit_model_runtime_override")

    def test_r2_thinking_probe_is_calibration_only_and_explicit(self):
        bundle=rc1_runner.config_bundle(); probe=rc1_runner._build_r2_thinking_probe(bundle)
        self.assertEqual(probe["model"],"qwen3.5:4b"); self.assertEqual(probe["prompt"],"What is 2 + 2? Give the final answer as 4.")
        self.assertEqual(probe["profile_config"]["num_ctx"],4096); self.assertTrue(probe["profile_config"]["think"])
        self.assertNotIn(probe["task_id"],[task["task_id"] for task in bundle["tasks"]["tasks"]])
        mock_response=rc1_runner.MockAdapter().infer(probe)
        self.assertIs(mock_response["request_payload"]["think"],True); self.assertEqual(mock_response["final_answer"],"4"); self.assertTrue(mock_response["thinking"])

    def test_mock_r2_stays_independent_and_reports_all_gates(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td)/"calibration_r2"; self.assertEqual(rc1_runner.main(["calibrate-r2","--mock","--run-dir",str(run)]),0)
            validation=json.loads((run/"calibration_r2_validation.json").read_text(encoding="utf-8"))
            self.assertTrue(validation["approved"]); self.assertEqual(set(validation["gates"]),{"scorer_path","thinking_separation","resume_dedup","tool_loop","image_path","embed_path","safety_parser","performance_path","raw_persistence"})
            self.assertFalse((run.parent/"public_results.jsonl").exists()); self.assertNotIn("olmo-3:7b-think", (run/"events.jsonl").read_text(encoding="utf-8"))

    def test_default_run_rejects_not_ready_without_inference(self):
        with tempfile.TemporaryDirectory() as td:
            result=rc1_runner.main(["run-all","--run-dir",str(Path(td)/"run")])
            self.assertEqual(result,2); self.assertFalse((Path(td)/"run"/"events.jsonl").exists())

    def test_mock_launch_doctor_calibration_run_finalize(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); template_hash=(ROOT/"config/run_config.template.json").read_bytes(); result=rc1_runner.main(["launch","--mock","--run-dir",str(root)])
            self.assertEqual(result,0); self.assertTrue((root/"approved_run_config.json").is_file()); self.assertTrue((root/"public_results.jsonl").is_file())
            self.assertEqual(template_hash,(ROOT/"config/run_config.template.json").read_bytes()); self.assertTrue(json.loads((root/"approved_run_config.json").read_text(encoding="utf-8"))["calibration_approved"])
            rows=[json.loads(x) for x in (root/"public_results.jsonl").read_text(encoding="utf-8").splitlines() if x]
            self.assertTrue(rows); self.assertTrue(all("final_answer" not in row and "raw_response" not in row for row in rows))

    def test_failed_calibration_blocks_launch_before_run(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with mock.patch.object(rc1_runner,"calibrate",return_value=2), mock.patch.object(rc1_runner,"_run_items") as run_items:
                result=rc1_runner.main(["launch","--mock","--run-dir",str(root)])
            self.assertEqual(result,2); run_items.assert_not_called()
            self.assertFalse((root/"approved_run_config.json").exists()); self.assertFalse((root/"public_results.jsonl").exists())

    def test_mock_tool_loop_handles_chain_and_zero_call(self):
        bundle=rc1_runner.config_bundle(); builder=rc1_runner.RC1ItemBuilder(bundle); adapter=rc1_runner.RC1Adapter(rc1_runner.MockAdapter(),True)
        items=builder.all_items(selected_model="functiongemma:270m")
        self.assertEqual(items[0]["tools"][0]["type"],"function"); self.assertIn("parameters",items[0]["tools"][0]["function"])
        zero=adapter.infer(next(x for x in items if x["task_id"]=="TOOL_04"))
        chain_item=next(x for x in builder.all_items() if x["task_id"]=="TOOL_08")
        chain=adapter.infer(chain_item)
        self.assertEqual(zero["status"],"completed"); self.assertEqual(zero["tool_calls"],[])
        self.assertEqual(chain["status"],"completed"); self.assertEqual(len(chain["tool_calls"]),2)

    def test_resume_does_not_duplicate_completed_mock_inference(self):
        with tempfile.TemporaryDirectory() as td:
            run=Path(td)/"run"; args=["run-all","--mock","--model","qwen3-embedding:latest","--task","EMB_Q01","--run-dir",str(run)]
            self.assertEqual(rc1_runner.main(args),0); first=(run/"events.jsonl").read_text(encoding="utf-8").count('"event":"inference_saved"')
            self.assertEqual(rc1_runner.main(["resume","--mock","--model","qwen3-embedding:latest","--task","EMB_Q01","--run-dir",str(run)]),0); second=(run/"events.jsonl").read_text(encoding="utf-8").count('"event":"inference_saved"')
            self.assertEqual(first,1); self.assertEqual(second,1)

    def test_private_raw_ignore_and_scorer_failure_persistence(self):
        self.assertIn("private_runs/", (ROOT/".gitignore").read_text(encoding="utf-8"))
        class FailingScorer:
            def score(self,evidence,item): raise RuntimeError("fixture scorer failure")
        class Adapter:
            def infer(self,item): return {"status":"completed","final_answer":"x","raw_response":[{"content":"x"}]}
        with tempfile.TemporaryDirectory() as td:
            item={"benchmark_version":"1.0-rc1","task_manifest_hash":"t","model_digest":"d","profile":"general","task_id":"T","model":"m"}
            store=EvidenceStore(Path(td)); breaker=CircuitBreaker(CircuitConfig(3,0,1),lambda:True,sleep=lambda _:None); Executor(store,Adapter(),FailingScorer(),breaker).run([item])
            self.assertTrue(list((Path(td)/"raw").rglob("*.json"))); self.assertIn("scoring_error",(Path(td)/"events.jsonl").read_text(encoding="utf-8"))

    def test_adapter_thinking_without_final_has_no_scope_error(self):
        adapter=OllamaAdapter(max_transport_retries=0)
        chunks=iter([b'{"message":{"thinking":"plan"},"done":true,"done_reason":"length"}\n'])
        class Response:
            def readline(self):
                try:return next(chunks)
                except StopIteration:return b""
        with mock.patch("scripts.ollama_adapter.urllib.request.urlopen",return_value=Response()):
            result=adapter.infer({"model":"m","prompt":"x","profile_config":{"think":True,"inactivity_timeout_seconds":1,"absolute_timeout_seconds":5},"capabilities":["thinking"]})
        self.assertEqual(result["status"],"truncated_before_final")

if __name__=="__main__": unittest.main()
