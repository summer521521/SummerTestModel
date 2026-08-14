import unittest

from scripts.regrade_practical_rc1 import (
    long_context_semantic_score,
    practical_score_record,
    safety_confusion,
    summarize,
    tool_dimensions,
    vision_semantic_score,
)


class PracticalRegradeTests(unittest.TestCase):
    def test_infrastructure_is_null_not_zero(self):
        result = practical_score_record({"inference_status": "connection_refused", "final_answer": None}, {"score": {"score": 0}}, {"track": "core"})
        self.assertIsNone(result["practical_score_0_to_100"])
        self.assertEqual(result["zero_score_category"], "infrastructure_failure")

    def test_no_final_is_recovery_eligible(self):
        result = practical_score_record({"inference_status": "truncated_before_final", "final_answer": None}, None, {"track": "reasoning"})
        self.assertTrue(result["recovery_eligible"])
        self.assertIsNone(result["practical_score_0_to_100"])

    def test_vision_and_long_context_answer_with_explanation_passes(self):
        for track, target in (("vision", "green triangle"), ("long_context", "7C4A-19D2")):
            result = practical_score_record({"inference_status": "completed", "final_answer": f"The observed target is {target}, as requested."}, None, {"track": track}, {"value": target})
            self.assertEqual(result["practical_score_0_to_100"], 100)
        self.assertEqual(vision_semantic_score("It is not a green triangle.", "green triangle"), 0)
        self.assertEqual(long_context_semantic_score("The checksum is 7C4A-19D2.", "7C4A-19D2"), 1)

    def test_code_protocol_keeps_hidden_test_score(self):
        result = practical_score_record({"inference_status": "completed", "final_answer": "```python\ndef f(): pass\n```"}, {"score": {"passed_tests": 8, "total_tests": 10, "protocol_score": 0.5}}, {"track": "code"})
        self.assertEqual(result["practical_score_0_to_100"], 84)

    def test_code_without_fence_loses_protocol_component(self):
        result = practical_score_record({"inference_status": "completed", "final_answer": "def f(): return 1"}, {"score": {"passed_tests": 10, "total_tests": 10}}, {"track": "code"})
        self.assertEqual(result["practical_score_0_to_100"], 80)

    def test_core_partial_structured_fields(self):
        result = practical_score_record({"task_id": "CORE_FMT_01", "inference_status": "completed", "final_answer": '{"status":"ready","count":2}'}, None, {"track": "core", "category": "format_instruction"}, {"value": '{"status":"ready","count":3}'})
        self.assertEqual(result["semantic_component"], 0.5)
        self.assertEqual(result["practical_score_0_to_100"], 70)

    def test_ocr_uses_aligned_similarity_and_completion(self):
        result = practical_score_record({"inference_status": "completed", "final_answer": "Invoice total: 128.40"}, None, {"track": "ocr"}, {"value": "Invoice total: 128.40"})
        self.assertEqual(result["practical_score_0_to_100"], 100)

    def test_truncated_ocr_keeps_semantics_but_loses_completion_credit(self):
        result = practical_score_record({"inference_status": "truncated", "final_answer": "Invoice total: 128.40"}, None, {"track": "ocr"}, {"value": "Invoice total: 128.40"})
        self.assertEqual(result["practical_score_0_to_100"], 90)
        self.assertEqual(result["completion_status"], "partial_usable_final")

    def test_tool_dimensions_use_trace_not_multi_step_flag(self):
        raw = {"final_answer": "Gold priority", "tool_trace": [{"role": "assistant", "tool_calls": [{"function": {"name": "lookup_order", "arguments": {"order_id": "O-77"}}}]}, {"role": "assistant", "tool_calls": [{"function": {"name": "get_customer", "arguments": {"customer_id": "C-9"}}}]}]}
        gt = {"expected_calls": [{"name": "lookup_order", "arguments": {"order_id": "O-77"}}, {"name": "get_customer", "arguments": {"customer_id": "C-9"}}], "required_final_facts": ["Gold", "priority"]}
        dimensions = tool_dimensions(raw, gt)
        self.assertEqual(dimensions["name_sequence"], 1)
        self.assertEqual(dimensions["argument_values"], 1)
        self.assertEqual(dimensions["final_facts"], 1)

    def test_tool_caps_are_independent_of_semantic_strict_score(self):
        raw = {"inference_status": "tool_not_found", "final_answer": "done", "tool_trace": []}
        gt = {"expected_calls": [{"name": "create_draft_event", "arguments": {"title": "Benchmark Review"}}]}
        result = practical_score_record(raw, {"score": {"score": 1.0, "multi_step_success": 1}}, {"track": "tools"}, gt)
        self.assertLessEqual(result["practical_score_0_to_100"], 40)

    def test_tool_trace_remains_scoreable_without_final_text(self):
        raw = {
            "inference_status": "tool_loop_limit",
            "final_answer": "",
            "tool_trace": [{"role": "assistant", "tool_calls": [{"function": {"name": "lookup", "arguments": {"id": "7"}}}]}],
        }
        gt = {"expected_calls": [{"name": "lookup", "arguments": {"id": "7"}}]}
        result = practical_score_record(raw, {"score": 0}, {"track": "tools"}, gt)
        self.assertIsNotNone(result["practical_score_0_to_100"])
        self.assertLessEqual(result["practical_score_0_to_100"], 60)

    def test_safety_is_per_record_and_confusion_metrics_are_model_level(self):
        rows = []
        for expected, predicted in (("unsafe", "unsafe"), ("safe", "safe"), ("safe", "unsafe"), ("unsafe", "safe")):
            result = practical_score_record({"inference_status": "completed", "final_answer": predicted}, None, {"track": "safety"}, {"label": expected})
            rows.append(result)
        metrics = safety_confusion(rows)
        self.assertEqual((metrics["tp"], metrics["tn"], metrics["fp"], metrics["fn"]), (1, 1, 1, 1))
        self.assertEqual(metrics["accuracy"], 0.5)

    def test_safety_confusion_ignores_unrelated_tracks(self):
        rows = [
            {"track": "core", "practical_score_0_to_100": 100},
            {"track": "safety", "safety_expected_label": "unsafe", "safety_predicted_label": "unsafe"},
        ]
        metrics = safety_confusion(rows)
        self.assertEqual(metrics["unknown"], 0)
        self.assertEqual(metrics["tp"], 1)

    def test_safety_summary_uses_accuracy_f1_composite(self):
        rows = []
        for expected, predicted in (("unsafe", "unsafe"), ("safe", "safe"), ("safe", "unsafe"), ("unsafe", "safe")):
            row = practical_score_record({"inference_status": "completed", "final_answer": predicted}, None, {"track": "safety"}, {"label": expected})
            row["track"] = "safety"
            rows.append(row)
        summary = summarize(rows, "safety")
        self.assertEqual(summary["tracks"]["safety"]["mean"], 50)
        self.assertEqual(summary["safety_confusion"]["unknown"], 0)

    def test_medical_partial_fields_uses_70_20_10(self):
        result = practical_score_record({"inference_status": "completed", "final_answer": "Metformin 500 mg twice daily with meals. Consult a doctor."}, None, {"track": "medical"}, {"records": [{"drug": "Metformin", "dose": "500 mg", "frequency": "twice daily with meals"}, {"drug": "Lisinopril", "dose": "10 mg", "frequency": "once each morning"}]})
        self.assertEqual(result["semantic_component"], 0.5)
        self.assertEqual(result["practical_score_0_to_100"], 65)

    def test_track_summary_exposes_completion_adjusted_mean(self):
        rows = [{"track": "core", "practical_score_0_to_100": 80, "completion_status": "usable_final"}, {"track": "core", "practical_score_0_to_100": None, "completion_status": "no_usable_final"}]
        summary = summarize(rows, "test")
        self.assertEqual(summary["tracks"]["core"]["completion_rate"], 0.5)
        self.assertEqual(summary["tracks"]["core"]["completion_adjusted_mean"], 40)

    def test_tool_caps(self):
        for status, cap in (("tool_not_found", 40), ("tool_loop_limit", 60)):
            result = practical_score_record({"inference_status": status, "final_answer": "done"}, {"score": {"score": 1.0}}, {"track": "tools"})
            self.assertLessEqual(result["practical_score_0_to_100"], cap)

    def test_embedding_without_final_answer_is_valid(self):
        result = practical_score_record({"inference_status": "completed", "embedding": [1, 0]}, {"score": {"recall_at_1": 1, "recall_at_3": 1, "recall_at_5": 1, "mrr": 1, "ndcg_at_5": 1}}, {"track": "embedding"})
        self.assertEqual(result["practical_score_0_to_100"], 100)

    def test_private_flat_translation_score_is_normalized(self):
        result = practical_score_record(
            {"inference_status": "completed", "final_answer": "translated"},
            {"score_0_to_10": 10, "normalized_score_0_to_1": 1.0},
            {"track": "translation"},
        )
        self.assertEqual(result["practical_score_0_to_100"], 100)


if __name__ == "__main__":
    unittest.main()
