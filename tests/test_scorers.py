import unittest
from scripts.scorers import *

class ScorerFamilyTests(unittest.TestCase):
    def test_exact_numeric_and_sequences(self):
        expected = 220 + 32 / 100
        self.assertTrue(exact("a\r\nb\n", "a\nb")); self.assertEqual(numeric("answer: " + str(expected), expected)["score"],1.0); self.assertEqual(numeric("1 or 2",1)["status"],"invalid_answer")
        self.assertTrue(ordered_sequence("A,B,C",["A","B","C"])); self.assertEqual(set_score(["a","b"],["b","a"]),1.0)
    def test_json_protocol_and_explanation(self):
        self.assertEqual(json_fields('{"x": 1}',{"x":1})["protocol_score"],1.0); self.assertEqual(json_fields('```json\n{"x": 1}\n```',{"x":1})["semantic_score"],1.0); self.assertEqual(extract_final("reason\nFINAL: 31"),"31")
    def test_checklist_unicode_and_ocr_repetition(self):
        self.assertEqual(checklist("中文 answer",{"中文":True})["score"],1.0); self.assertTrue(ocr_score("ABC ABC ABC ABC","ABC")["repetition_degeneration"])
    def test_tool_safety_and_metrics(self):
        actual={"tool_calls":[{"name":"x","arguments":{"v":2.5}}]}; expected={"expected_calls":[{"name":"x","arguments":{"v":2.5}}]}
        self.assertEqual(tool_trace_validator(actual,expected)["score"],1.0); self.assertEqual(parse_safety(" <score> yes </score> ","guardian"),1); self.assertEqual(classification_metrics([1,0],[1,0])["f1"],1.0)
    def test_missing_final_never_falls_back_to_raw_stream(self):
        evidence={"final_answer":None,"raw_response":[{"message":{"content":"<score> yes </score>"}}],"model":"granite4.1-guardian:8b"}
        safety=score_task(evidence,{}, {"label":"safe"}, {"type":"classification_metrics"})
        self.assertEqual(safety["status"],"invalid_response"); self.assertIsNone(safety["prediction"]); self.assertEqual(safety["invalid_response_count"],1)
        text=score_task({"final_answer":None,"raw_response":[{"content":"expected"}]},{},{"value":"expected"},{"type":"long_context_exact"})
        self.assertEqual(text["score"],0.0)
    def test_retrieval(self): self.assertEqual(cosine_retrieval([("D1",.9),("D2",.1)],["D1"])["mrr"],1.0)
if __name__ == "__main__": unittest.main()
