import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import rc1_runner
from scripts.executor_core import CircuitBreaker, CircuitConfig, EvidenceStore, Executor
from scripts.ollama_adapter import OllamaAdapter


ROOT = Path(__file__).resolve().parents[1]


class _StreamResponse:
    status = 200

    def __init__(self, lines):
        self.lines = iter(lines)

    def readline(self):
        try:
            return next(self.lines)
        except StopIteration:
            return b""


class R3PolicyTests(unittest.TestCase):
    def _infer(self, item, lines):
        with mock.patch("scripts.ollama_adapter.urllib.request.urlopen", return_value=_StreamResponse(lines)) as opened:
            result = OllamaAdapter(max_transport_retries=0).infer(item)
        return result, opened

    def test_native_sampling_and_thinking_requests(self):
        base = {"model": "qwen3.5:4b", "prompt": "x", "capabilities": ["thinking"], "profile_config": {"num_ctx": 8192, "num_predict": 8192, "inactivity_timeout_seconds": 1, "absolute_timeout_seconds": 5}}
        result, _ = self._infer(base, [b'{"response":"ok","done":true,"done_reason":"stop"}\n'])
        options = result["request_payload"]["options"]
        self.assertFalse(set(options) & {"temperature", "top_k", "top_p", "min_p", "typical_p", "repeat_penalty", "presence_penalty", "frequency_penalty", "seed"})
        self.assertNotIn("think", result["request_payload"])
        reasoning = {**base, "profile_config": {"num_ctx": 32768, "num_predict": 16384, "think": True, "inactivity_timeout_seconds": 1, "absolute_timeout_seconds": 5}}
        result, _ = self._infer(reasoning, [b'{"message":{"thinking":"plan"}}\n', b'{"message":{"content":"4"},"done":true,"done_reason":"stop"}\n'])
        self.assertIs(result["request_payload"]["think"], True)
        performance = {**base, "capabilities": [], "profile_config": {"num_ctx": 4096, "num_predict": 512, "think": False, "inactivity_timeout_seconds": 1, "absolute_timeout_seconds": 5}}
        result, _ = self._infer(performance, [b'{"response":"ok","done":true,"done_reason":"stop"}\n'])
        self.assertIs(result["request_payload"]["think"], False)

    def test_exact_r3_profile_limits_and_soft_limit_only_reports(self):
        profiles = json.loads((ROOT / "config/generation_profiles.rc1.json").read_text(encoding="utf-8"))["profiles"]
        self.assertEqual((profiles["general"]["num_ctx"], profiles["general"]["num_predict"], profiles["general"]["inactivity_timeout_seconds"], profiles["general"]["absolute_timeout_seconds"], profiles["general"]["practical_soft_limit_seconds"]), (8192, 8192, 180, 600, 120))
        self.assertEqual((profiles["reasoning"]["num_ctx"], profiles["reasoning"]["num_predict"], profiles["reasoning"]["inactivity_timeout_seconds"], profiles["reasoning"]["absolute_timeout_seconds"], profiles["reasoning"]["practical_soft_limit_seconds"]), (32768, 16384, 300, 1200, 240))
        self.assertEqual((profiles["tools"]["absolute_timeout_seconds"], profiles["tools"]["max_tool_rounds"]), (300, 3))
        result, _ = self._infer({"model": "m", "prompt": "x", "profile_config": {"num_ctx": 1, "num_predict": 1, "practical_soft_limit_seconds": -1, "inactivity_timeout_seconds": 1, "absolute_timeout_seconds": 5}}, [b'{"response":"ok","done":true,"done_reason":"stop"}\n'])
        self.assertEqual(result["status"], "completed")
        self.assertFalse(result["timing"]["practical_within_soft_limit"])

    def test_interrupted_before_and_after_output_preserve_evidence(self):
        item = {"model": "m", "prompt": "x", "profile_config": {"inactivity_timeout_seconds": 1, "absolute_timeout_seconds": 5}}
        before, _ = self._infer(item, [b'{"load_duration":1}\n'])
        self.assertEqual(before["status"], "stream_interrupted_before_output")
        self.assertEqual(before["streamed_chunks"], [{"load_duration": 1}])
        self.assertFalse(before["terminal_record_seen"])
        after, _ = self._infer(item, [b'{"response":"partial"}\n'])
        self.assertEqual(after["status"], "stream_interrupted_after_output")
        self.assertEqual(after["final_answer"], "partial")
        self.assertFalse(after["completion_terminal_record"])
        self.assertTrue(after["runtime_anomaly"])
        self.assertIn("time_to_first_final_seconds", after["timing"])

    def test_preload_order_and_after_output_resume_dedup(self):
        calls = []

        class Base:
            def unload(self, model):
                calls.append(("unload", model))
                return True

            def preload(self, model, keep_alive, version):
                calls.append(("preload", model, keep_alive))
                return {"status": "completed", "model": model, "request_payload": {"model": model, "keep_alive": "5m"}, "request_started_at": "2026-08-09T12:00:00+08:00", "request_finished_at": "2026-08-09T12:00:01+08:00"}

            def infer(self, item):
                calls.append(("infer", item["model"]))
                return {"status": "completed", "final_answer": "ok", "terminal_record_seen": True, "completion_terminal_record": True, "timing": {"request_started_at": "2026-08-09T12:00:02+08:00", "request_finished_at": "2026-08-09T12:00:03+08:00"}}

        adapter = rc1_runner.RC1Adapter(Base())
        item = {"model": "a", "track": "core", "sampling_policy": "native_artifact"}
        self.assertEqual(adapter.infer(item)["preload"]["request_payload"]["keep_alive"], "5m")
        adapter.infer({**item, "model": "b"})
        self.assertEqual(calls[:4], [("preload", "a", "5m"), ("infer", "a"), ("unload", "a"), ("preload", "b", "5m")])

        class Once:
            def __init__(self): self.calls = 0
            def infer(self, _):
                self.calls += 1
                return {"status": "stream_interrupted_after_output", "final_answer": "partial", "raw_response": [{"response": "partial"}], "streamed_chunks": [{"response": "partial"}], "terminal_record_seen": False, "completion_terminal_record": False, "runtime_anomaly": True}

        benchmark_item = {"benchmark_version": "1.0-rc1", "task_manifest_hash": "t", "model_digest": "d", "profile": "general", "task_id": "T", "model": "m"}
        with tempfile.TemporaryDirectory() as td:
            once = Once(); store = EvidenceStore(Path(td)); breaker = CircuitBreaker(CircuitConfig(3, 0, 1), lambda: True, sleep=lambda _: None)
            Executor(store, once, lambda: None, breaker).run([benchmark_item])
            Executor(store, once, lambda: None, breaker).run([benchmark_item])
            self.assertEqual(once.calls, 1)

    def test_r3_manifest_runtime_snapshot_and_reference_scaffold(self):
        import jsonschema
        tasks = json.loads((ROOT / "config/task_manifest.rc1.public.json").read_text(encoding="utf-8"))
        self.assertEqual((tasks["task_count"], tasks["scored_task_count"], tasks["diagnostic_task_count"], tasks["telemetry_task_count"]), (119, 116, 1, 2))
        self.assertNotIn("PERF_01", {task["task_id"] for task in tasks["tasks"]})
        plan = json.loads((ROOT / "config/model_execution_plan.rc1.public.json").read_text(encoding="utf-8"))
        self.assertEqual(len(plan["models"]), 39)
        self.assertEqual(sum(any(task.startswith("PERF_") for task in model["task_ids"]) for model in plan["models"]), 29)
        snapshot = json.loads((ROOT / "inventory/model_runtime_defaults.rc1.json").read_text(encoding="utf-8"))
        jsonschema.validate(snapshot, json.loads((ROOT / "config/model_runtime_defaults.schema.json").read_text(encoding="utf-8")))
        self.assertEqual(len(snapshot["models"]), 39)
        self.assertTrue(all(set(row["visible_declared_defaults"]) == {"temperature", "top_k", "top_p", "min_p", "repeat_penalty"} for row in snapshot["models"]))
        self.assertNotIn("TEMPLATE", (ROOT / "inventory/model_runtime_defaults.rc1.json").read_text(encoding="utf-8"))
        self.assertTrue((ROOT / "docs/model_reference_policy.md").is_file())
        self.assertTrue((ROOT / "config/model_reference.schema.json").is_file())
        self.assertTrue((ROOT / "models/reference/_template.json").is_file())
        jsonschema.validate(json.loads((ROOT / "models/reference/_template.json").read_text(encoding="utf-8")), json.loads((ROOT / "config/model_reference.schema.json").read_text(encoding="utf-8")))

    def test_mock_r3_calibration_passes_without_baseline_output(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td) / "calibration_r3"
            self.assertEqual(rc1_runner.main(["calibrate-r3", "--mock", "--run-dir", str(run)]), 0)
            self.assertTrue(json.loads((run / "calibration_r3_validation.json").read_text(encoding="utf-8"))["approved"])
            self.assertFalse((run.parent / "public_results.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
