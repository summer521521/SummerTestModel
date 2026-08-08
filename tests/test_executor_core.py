from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.executor_core import CircuitBreaker, CircuitConfig, EvidenceStore, Executor, SafeCodeHarness
from scripts.luna_executor import MockAdapter, MockScorer, doctor, mock_run
import scripts.luna_executor as luna_executor
from scripts.ollama_adapter import OllamaAdapter
from scripts.tool_loop import ToolLoopEngine


class ExecutorTests(unittest.TestCase):
    def test_mock_failure_isolation_resume_and_duplicate_skip(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = mock_run(Path(temporary))
            self.assertEqual(result["state_items"], 13)
            self.assertTrue(result["duplicate_skipped"])
            self.assertGreaterEqual(result["raw_files"], 13)

    def test_corrupt_state_is_quarantined_and_rebuilt(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = EvidenceStore(Path(temporary))
            store.state_path.write_text("{", encoding="utf-8")
            state = store.load_state()
            self.assertEqual(state["version"], 1)
            self.assertTrue(list(Path(temporary).glob("state.corrupt.*.json")))

    def test_partial_temp_write_does_not_replace_valid_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = EvidenceStore(Path(temporary))
            store.checkpoint({"version": 1, "items": {"stable": {"inference_status": "completed"}}})
            store.state_path.with_suffix(".json.tmp").write_text("{", encoding="utf-8")
            state = store.load_state()
            self.assertIn("stable", state["items"])

    def test_code_harness_pass_timeout_and_block(self):
        passed = SafeCodeHarness.run_fixture("def add(a, b): return a + b", "assert add(2, 3) == 5")
        self.assertEqual(passed["status"], "passed")
        timed = SafeCodeHarness.run_fixture("def spin():\n    while True: pass", "spin()", timeout_seconds=0.2)
        self.assertEqual(timed["status"], "timeout")
        with self.assertRaises(ValueError):
            SafeCodeHarness.run_fixture("import os", "assert True")

    def test_circuit_breaker_opens_and_recovers(self):
        health = iter([False, False, True])
        breaker = CircuitBreaker(CircuitConfig(2, 0, 5), lambda: next(health), sleep=lambda _: None)
        breaker.failure("connection_refused")
        breaker.failure("connection_refused")
        self.assertTrue(breaker.permit())
        self.assertTrue(breaker.permit())

    def test_logical_key_includes_task_manifest_hash(self):
        from scripts.executor_core import logical_key
        base = {"benchmark_version":"1", "task_manifest_hash":"a", "model_digest":"d", "profile":"p", "task_id":"t"}
        self.assertNotEqual(logical_key(base), logical_key({**base, "task_manifest_hash":"b"}))

    def test_resume_gate_skips_terminal_and_retries_stream_interrupted(self):
        class SequenceAdapter:
            def __init__(self): self.calls=0
            def infer(self, item):
                self.calls += 1
                if self.calls == 1: return {"status":"stream_interrupted","raw_response":[{"partial":"x"}]}
                return {"status":"completed","final_answer":"ok","raw_response":[{"content":"ok"}]}
        class Scorer:
            def score(self, evidence, item): return {"status":"scored","score":1.0}
        item={"benchmark_version":"1.0-rc1","task_manifest_hash":"t","model_digest":"d","profile":"general","task_id":"T","model":"m"}
        with tempfile.TemporaryDirectory() as td:
            run=Path(td); adapter=SequenceAdapter(); scorer=Scorer()
            Executor(EvidenceStore(run),adapter,scorer,CircuitBreaker(CircuitConfig(3,0,1),lambda:True,sleep=lambda _:None)).run([item])
            first=(run/"events.jsonl").read_text(encoding="utf-8").count('"event":"inference_saved"')
            self.assertEqual(first,1)
            Executor(EvidenceStore(run),adapter,scorer,CircuitBreaker(CircuitConfig(3,0,1),lambda:True,sleep=lambda _:None)).run([item])
            second=(run/"events.jsonl").read_text(encoding="utf-8").count('"event":"inference_saved"')
            self.assertEqual(second,2); self.assertEqual(adapter.calls,2)

    def test_tool_loop_fixture_and_limit(self):
        calls = iter([{"tool_calls":[{"function":{"name":"fixture","arguments":{"x":2}}}]}, {"content":"done"}])
        result = ToolLoopEngine({"fixture": lambda args: args["x"] * 2}).run([], lambda _: next(calls))
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["messages"][-2]["content"], 4)
        limited = ToolLoopEngine({"fixture": lambda _: 1}, max_rounds=1).run([], lambda _: {"tool_calls":[{"name":"fixture","arguments":{}}]})
        self.assertEqual(limited["status"], "tool_loop_limit")

    def test_adapter_separates_thinking_and_answer_without_format(self):
        adapter = OllamaAdapter(max_transport_retries=0)
        chunks = iter([b'{"message":{"thinking":"plan"}}\n', b'{"message":{"content":"answer"},"done":true,"done_reason":"stop","eval_count":2}\n'])
        class Response:
            def readline(self):
                try: return next(chunks)
                except StopIteration: return b""
        with mock.patch("scripts.ollama_adapter.urllib.request.urlopen", return_value=Response()):
            result = adapter.infer({"model":"m","messages":[{"role":"user","content":"x"}],"profile_config":{"think":True,"inactivity_timeout_seconds":1,"absolute_timeout_seconds":5},"capabilities":["thinking"]})
        self.assertEqual(result["thinking"], "plan")
        self.assertEqual(result["final_answer"], "answer")
        self.assertNotIn("format", result["request_payload"])
        self.assertTrue(result["request_payload"]["think"])
        self.assertEqual(adapter._think({"think":False}, ["completion"])[0], None)

    def test_doctor_ready_path_with_frozen_mock_manifests(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            asset = root / "asset.txt"
            asset.write_text("fixture", encoding="utf-8")
            asset_hash = hashlib.sha256(asset.read_bytes()).hexdigest()
            files = {
                "benchmark_manifest": {"benchmark_version": "mock-v1"},
                "task_manifest": {"tasks": [{"task_id": "T1", "version": "1", "assets": [{"path": "asset.txt", "sha256": asset_hash}]}]},
                "scorer_manifest": {"scorers": []},
                "model_execution_plan": {"models": [{"model": "mock:model", "digest": "d", "local_or_cloud": "local", "profiles": ["p"], "task_ids": ["T1"]}]},
                "generation_profiles": {"profiles": {"p": {}}},
                "retry_policy": {"max_transport_retries": 0},
            }
            hashes = {}
            config = {
                "ollama_api": "http://mock.invalid",
                "inventory_path": "inventory.json",
                "output_dir": "output",
                "unload_between_models": True,
                "warmup_behavior": "none",
            }
            (root / "inventory.json").write_text(json.dumps({"models": [{"exact_name": "mock:model", "digest": "d"}]}), encoding="utf-8")
            for key, value in files.items():
                path = root / f"{key}.json"
                path.write_text(json.dumps(value), encoding="utf-8")
                config[key] = path.name
                hashes[key] = hashlib.sha256(path.read_bytes()).hexdigest()
            config["manifest_hashes"] = hashes
            config_path = root / "run_config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            with mock.patch.object(luna_executor, "ROOT", root), mock.patch.object(luna_executor, "healthcheck", return_value=True):
                result, checks = doctor(config_path)
            self.assertEqual(result, "READY", checks)


if __name__ == "__main__":
    unittest.main()
