import copy
import unittest

from scripts.incremental_model import build_bundle


class IncrementalModelTests(unittest.TestCase):
    def base(self):
        return {
            "benchmark": {"benchmark_version": "1.0-rc1"},
            "config": {"scorer_version": "1.0-rc1.1", "manifest_hashes": {"task_manifest": "abc"}},
            "plan": {"selection_policy": {"max_total_params_b": 10.0}, "models": [{"model": "reference:1b", "digest": "a" * 64, "local_or_cloud": "local", "assigned_tracks": ["core", "tools"], "task_ids": ["CORE_FMT_01", "TOOL_01"], "retention_status": "UNASSESSED"}]},
            "inventory": {"models": [{"exact_name": "reference:1b", "capabilities": ["completion", "tools"]}]},
            "runtime_defaults": {"models": []},
        }

    def snapshot(self):
        return {"exact_name": "new:2b", "digest": "b" * 64, "disk_size_bytes": 2_000_000_000, "parameter_size": "2B", "capabilities": ["completion", "tools"], "local_or_cloud": "local"}

    def test_explicit_reference_copies_frozen_tasks(self):
        base = self.base()
        bundle, plan = build_bundle(base, self.snapshot(), "reference:1b")
        self.assertEqual(plan["task_ids"], ["CORE_FMT_01", "TOOL_01"])
        self.assertEqual(bundle["plan"]["models"][0]["model"], "new:2b")
        self.assertEqual(bundle["plan"]["models"][0]["retention_status"], "UNASSESSED")
        self.assertEqual(base["plan"]["models"][0]["model"], "reference:1b")

    def test_missing_capability_fails_closed(self):
        snapshot = copy.deepcopy(self.snapshot())
        snapshot["capabilities"] = ["completion"]
        with self.assertRaisesRegex(ValueError, "lacks capabilities"):
            build_bundle(self.base(), snapshot, "reference:1b")

    def test_existing_baseline_model_is_not_retested(self):
        base = self.base()
        base["plan"]["models"].append({"model": "another:1b", "digest": "c" * 64, "local_or_cloud": "local", "assigned_tracks": ["core"], "task_ids": ["CORE_FMT_01"]})
        with self.assertRaisesRegex(ValueError, "already exists"):
            build_bundle(base, {"exact_name": "reference:1b", "digest": "a" * 64, "disk_size_bytes": 2_000_000_000, "parameter_size": "1B", "capabilities": ["completion", "tools"]}, "another:1b")

    def test_out_of_scope_or_cloud_stub_is_rejected(self):
        too_large = copy.deepcopy(self.snapshot())
        too_large["parameter_size"] = "12B"
        with self.assertRaisesRegex(ValueError, "exceeds the frozen local scope"):
            build_bundle(self.base(), too_large, "reference:1b")
        cloud_stub = copy.deepcopy(self.snapshot())
        cloud_stub["disk_size_bytes"] = 388
        with self.assertRaisesRegex(ValueError, "substantive local model file"):
            build_bundle(self.base(), cloud_stub, "reference:1b")


if __name__ == "__main__":
    unittest.main()
