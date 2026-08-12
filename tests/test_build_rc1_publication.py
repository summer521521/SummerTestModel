import unittest

from scripts.build_rc1_publication import capability_score, official_reference_rows, task_track


class PublicationBuilderTests(unittest.TestCase):
    def test_track_mapping(self):
        self.assertEqual(task_track("CORE_FMT_01"), "core")
        self.assertEqual(task_track("UNSAFE01"), "safety")
        self.assertEqual(task_track("PERF_COLD_01"), "performance")

    def test_track_specific_score_fields(self):
        self.assertEqual(capability_score({"score": {"task_score": 0.75}}, "core"), 0.75)
        self.assertEqual(capability_score({"score": {"ndcg_at_5": 1.0}}, "embedding"), 1.0)
        self.assertIsNone(capability_score({"score": {"status": "completed"}}, "performance"))

    def test_official_source_matrix_covers_local_inventory(self):
        rows = official_reference_rows()
        self.assertEqual(len(rows), 39)
        self.assertEqual(len({row["model"] for row in rows}), 39)
        self.assertTrue(all(row["comparison_rule"] == "CONTEXT_ONLY_NOT_NUMERICALLY_COMPARABLE_TO_RC1" for row in rows))


if __name__ == "__main__":
    unittest.main()
