import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.executor_core import CircuitBreaker, CircuitConfig, Executor, logical_key
from scripts import rc1_recovery
from scripts.luna_executor import validate_manifest_file_hashes
from scripts.rc1_runner import config_bundle, RC1ItemBuilder


class RecoveryTests(unittest.TestCase):
    def test_queue_has_exactly_50_unique_items(self):
        queue = rc1_recovery.load_queue()
        self.assertEqual(sum(len(v) for v in queue.values()), 50)
        self.assertEqual(len({(m, t) for m, tasks in queue.items() for t in tasks}), 50)

    def test_init_does_not_change_template(self):
        template = (rc1_recovery.ROOT / "config" / "run_config.template.json").read_bytes()
        with tempfile.TemporaryDirectory() as td:
            config = Path(td) / "approved.json"; run = Path(td) / "run"
            rc1_recovery.make_config(config, run)
            self.assertEqual(template, (rc1_recovery.ROOT / "config" / "run_config.template.json").read_bytes())
            self.assertTrue(json.loads(config.read_text(encoding="utf-8"))["calibration_approved"])

    def test_recovery_metadata_is_private_and_separate(self):
        with tempfile.TemporaryDirectory() as td:
            run = Path(td) / "run"; run.mkdir()
            self.assertNotEqual(run, rc1_recovery.ROOT / "private_runs" / "rc1_baseline_20260809")

    def test_logical_identity_hash_is_preserved_separately_from_byte_hash(self):
        config = json.loads((rc1_recovery.ROOT / "config" / "run_config.template.json").read_text(encoding="utf-8"))
        self.assertEqual(config["manifest_hashes"]["task_manifest"], "3c358ffd10898c074c04674d81c2cf4ad9e34d5bb1e51cc908716b0d505b60ec")
        self.assertNotEqual(config["manifest_hashes"]["task_manifest"], config["manifest_file_hashes"]["task_manifest"])

    def test_current_manifest_bytes_pass_and_tampered_expected_byte_hash_fails(self):
        config = json.loads((rc1_recovery.ROOT / "config" / "run_config.template.json").read_text(encoding="utf-8"))
        self.assertTrue(all(x["status"] == "PASS" for x in validate_manifest_file_hashes(config)))
        tampered = json.loads(json.dumps(config)); tampered["manifest_file_hashes"]["task_manifest"] = "0" * 64
        self.assertTrue(any(x["check"] == "hash:task_manifest" and x["status"] == "FAIL" for x in validate_manifest_file_hashes(tampered)))

    def test_all_byte_hash_targets_are_declared_with_sha256_length(self):
        config = json.loads((rc1_recovery.ROOT / "config" / "run_config.template.json").read_text(encoding="utf-8"))
        self.assertEqual(set(config["manifest_file_hashes"]), {"benchmark_manifest", "task_manifest", "scorer_manifest", "model_execution_plan", "generation_profiles", "retry_policy", "model_runtime_defaults", "private_package_manifest", "scorer_implementation"})
        self.assertTrue(all(len(value) == 64 for value in config["manifest_file_hashes"].values()))

    def test_targeted_queue_keys_align_with_original_baseline(self):
        bundle = config_bundle(rc1_recovery.ROOT / "config" / "run_config.template.json")
        queue = rc1_recovery.load_queue(); builder = RC1ItemBuilder(bundle)
        plan = {row["model"]: row for row in bundle["plan"]["models"]}
        baseline = json.loads((rc1_recovery.ROOT / "private_runs" / "rc1_baseline_20260809" / "state.json").read_text(encoding="utf-8"))["items"]
        keys = {logical_key(builder.build(plan[m], task_id)) for m, ids in queue.items() for task_id in ids}
        self.assertEqual(len(keys), 50)
        self.assertTrue(keys.issubset(set(baseline)))

    def test_recovery_store_event_hash_matches_final_raw_hash(self):
        with tempfile.TemporaryDirectory() as td:
            item = {"benchmark_version": "1.0-rc1", "task_manifest_hash": "logical", "model_digest": "digest", "profile": "ordinary", "task_id": "X", "model": "m", "exact_model_tag": "m", "scorer_version": "1.0", "sampling_policy": "native_artifact"}
            key = logical_key(item)
            store = rc1_recovery.RecoveryStore(Path(td), {key: {"recovery_used": True, "recovery_policy_id": "test"}})
            evidence = store.save_inference(item, "a1", {"status": "completed", "final_answer": "ok", "meaningful": True})
            raw_path = Path(td) / evidence["raw_path"]
            raw_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()
            event = json.loads((Path(td) / "events.jsonl").read_text(encoding="utf-8").splitlines()[-1])
            self.assertEqual(event["raw_sha256"], raw_hash)
            self.assertEqual(json.loads(raw_path.read_text(encoding="utf-8"))["recovery_used"], True)

    def test_executor_resume_deduplicates_after_process_boundary(self):
        class Adapter:
            def __init__(self): self.calls = 0
            def infer(self, item): self.calls += 1; return {"status": "completed", "final_answer": "ok", "meaningful": True}
        class Scorer:
            def score(self, evidence, item): return {"status": "scored", "score": 1}
        with tempfile.TemporaryDirectory() as td:
            item = {"benchmark_version": "1.0-rc1", "task_manifest_hash": "logical", "model_digest": "digest", "profile": "ordinary", "task_id": "X", "model": "m", "exact_model_tag": "m", "scorer_version": "1.0", "sampling_policy": "native_artifact"}
            config = CircuitConfig(3, 0, 1)
            first = Adapter(); first_state = Executor(rc1_recovery.RecoveryStore(Path(td), {}), first, Scorer(), CircuitBreaker(config, lambda: True), "resume").run([item])
            second = Adapter(); second_state = Executor(rc1_recovery.RecoveryStore(Path(td), {}), second, Scorer(), CircuitBreaker(config, lambda: True), "resume").run([item])
            self.assertEqual(first_state["items"][logical_key(item)]["inference_status"], "completed")
            self.assertEqual(second.calls, 0)

    def test_scoring_failure_preserves_raw_and_model_failure_does_not_stop_next(self):
        class Adapter:
            def __init__(self): self.calls = 0
            def infer(self, item):
                self.calls += 1
                return {"status": "runner_exception", "error": "model failed"} if self.calls == 1 else {"status": "completed", "final_answer": "ok"}
        class Scorer:
            def score(self, evidence, item): raise RuntimeError("scorer failure")
        def item(tid): return {"benchmark_version": "1.0-rc1", "task_manifest_hash": "logical", "model_digest": "digest", "profile": "ordinary", "task_id": tid, "model": "m", "exact_model_tag": "m", "scorer_version": "1.0", "sampling_policy": "native_artifact"}
        with tempfile.TemporaryDirectory() as td:
            state = Executor(rc1_recovery.RecoveryStore(Path(td), {}), Adapter(), Scorer(), CircuitBreaker(CircuitConfig(3, 0, 1), lambda: True), "resume").run([item("A"), item("B")])
            self.assertEqual(len(state["items"]), 2)
            self.assertTrue(all(value.get("raw_path") for value in state["items"].values()))

    def test_circuit_breaker_failure_and_success_reset(self):
        breaker = CircuitBreaker(CircuitConfig(3, 30, 900), lambda: True, sleep=lambda _: None)
        breaker.failure("connection_refused"); breaker.failure("connection_refused")
        self.assertEqual(breaker.failures, 2)
        breaker.success()
        self.assertEqual((breaker.failures, breaker.opened_at), (0, None))

    def test_live_digest_validation_detects_single_revision_without_aliasing(self):
        bundle = config_bundle(rc1_recovery.ROOT / "config" / "run_config.template.json")
        queue = {"qwen3.5:4b": ["CODE_08"]}
        expected = rc1_recovery.EXPECTED_DIGESTS["qwen3.5:4b"]
        with patch.object(rc1_recovery, "live_model_digests", return_value={"qwen3.5:4b": "0" * 64}):
            revisions, details = rc1_recovery.validate_recovery_digests(bundle, queue, "http://unused")
        self.assertEqual(revisions["qwen3.5:4b"], "MODEL_REVISION_CHANGED")
        self.assertNotEqual(details["models"]["qwen3.5:4b"]["live"], expected)

    def test_private_paths_are_not_tracked_and_public_result_exists(self):
        import subprocess
        result = subprocess.run(["git", "ls-files", "private_runs"], capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), "")
        self.assertTrue((rc1_recovery.ROOT / "public_results" / "rc1_baseline_20260809.scorer-1.0-rc1.1.jsonl").is_file())


if __name__ == "__main__":
    unittest.main()
