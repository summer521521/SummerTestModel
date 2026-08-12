import unittest
from scripts.phase3r_validator import validate
from scripts.scorers import levenshtein, numeric, ocr_score
import json
from pathlib import Path
import tempfile
from PIL import Image

class Phase3RRegressionTests(unittest.TestCase):
    def test_old_phase3_freeze_is_detected_as_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); (root/"config").mkdir(); private=root/"private_benchmark/1.0-rc1"; (private/"tasks").mkdir(parents=True); (private/"ground_truth").mkdir(); (private/"assets").mkdir(); (private/"hidden_tests").mkdir()
            (root/"config/task_manifest.rc1.public.json").write_text(json.dumps({"tasks":[{"task_id":"T1","scored":True,"category":"bad","profile":"long_context_8k_or_32k","prompt_sha256":"a","ground_truth_sha256":"a"}]}),encoding="utf-8")
            (root/"config/scorer_manifest.rc1.public.json").write_text(json.dumps({"scorers":[{}]}),encoding="utf-8")
            (private/"tasks/T1.txt").write_text("same",encoding="utf-8"); (private/"ground_truth/T1.txt").write_text("same",encoding="utf-8")
            Image.new("RGB",(1200,500),"white").save(private/"assets/VIS_01.png")
            result=validate(root)
        self.assertFalse(result["valid"])
        self.assertGreater(result["metrics"]["prompt_gt_identical_before_or_current"],0)
        self.assertGreater(result["metrics"]["private_payload_identical"],0)
        self.assertGreater(result["metrics"]["placeholder_assets"],0)
        self.assertGreater(result["metrics"]["missing_structured_code_tests"],0)
        self.assertGreater(result["metrics"]["schema_errors"],0)

    def test_repaired_freeze_is_valid(self):
        result=validate()
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["metrics"]["prompt_gt_identical_before_or_current"],0)
        self.assertEqual(result["metrics"]["private_payload_identical"],0)
        self.assertEqual(result["metrics"]["placeholder_assets"],0)
        self.assertEqual(result["metrics"]["missing_structured_code_tests"],0)

    def test_cer_and_numeric_final_line(self):
        self.assertEqual(levenshtein("axbc","abc")["edit_distance"],1)
        self.assertAlmostEqual(levenshtein("axbc","abc")["cer"],1/3)
        self.assertEqual(numeric("240 discounted\nFINAL: " + str(220+32/100),220+32/100)["score"],1.0)
        self.assertEqual(numeric("wrong 999\nFINAL: 31",31)["score"],1.0)
        self.assertGreater(ocr_score("abcabcabcabc","abc")["cer"],0)

    def test_structured_counts_and_profiles(self):
        root=Path("private_benchmark/1.0-rc1")
        self.assertEqual(len(list((root/"hidden_tests").glob("CODE_*.json"))),8)
        self.assertTrue(all(len(json.loads(p.read_text(encoding="utf-8"))["cases"])==10 for p in (root/"hidden_tests").glob("CODE_*.json")))
        self.assertEqual(len(json.loads((root/"embedding/corpus.json").read_text(encoding="utf-8"))),24)
        self.assertEqual(len(json.loads((root/"embedding/queries.json").read_text(encoding="utf-8"))),12)
        self.assertEqual(len(json.loads((root/"safety/tasks.json").read_text(encoding="utf-8"))),20)
        tasks=json.loads(Path("config/task_manifest.rc1.public.json").read_text(encoding="utf-8"))["tasks"]
        self.assertEqual({x["profile"] for x in tasks if x["task_id"].startswith("CTX8")},{"long_context_8k"})
        self.assertEqual({x["profile"] for x in tasks if x["task_id"].startswith("CTX32")},{"long_context_32k"})
        self.assertEqual(sum(x["scored"] for x in tasks),116)

if __name__=="__main__": unittest.main()
