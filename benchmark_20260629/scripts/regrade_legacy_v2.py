"""Non-destructive V2 analysis of the 20260730 incremental raw JSONL."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from benchmark_v2 import ROOT, code_policy, run_code_child, safe_name


OLD = ROOT / "benchmark_20260629" / "runs" / "20260730_incremental"
OUT = ROOT / "benchmark_20260629" / "runs" / "derived" / "regrade_20260730_v2"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    source = OLD / "results.jsonl"
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        status = item.get("status", "")
        answer = item.get("response", "")
        if not answer:
            raw = OLD / "raw" / safe_name(item.get("model", "")) / f"core_{item.get('test_id','')}.json"
            if raw.exists():
                try:
                    payload = json.loads(raw.read_text(encoding="utf-8")); answer = ((payload.get("response") or {}).get("response", ""))
                    item["thinking"] = ((payload.get("response") or {}).get("thinking", ""))
                except Exception:
                    pass
        perf = item.get("performance") or {}
        done_reason = item.get("done_reason") or perf.get("done_reason")
        if status == "failed":
            classification = "transport_failure"
        elif done_reason == "length" and not answer:
            classification = "truncated_before_final_answer"
        elif done_reason == "length":
            classification = "truncated"
        elif status == "unsafe_to_execute":
            classification = "grader_policy_rejected"
        elif answer:
            classification = "completed_with_final_answer"
        else:
            classification = "empty_response_with_thinking" if item.get("thinking") else "empty_response"
        revised = ""
        revised_score = ""
        if item.get("test_id") == "code_bugfix" and answer:
            code = answer
            fenced = __import__("re").search(r"```(?:python)?\s*(.*?)```", answer, flags=__import__("re").S)
            if fenced: code = fenced.group(1)
            revised, note = code_policy(code)
            revised = "policy_pass" if revised == "ok" else revised
            revised_score, revised_status, _ = run_code_child(code, "CODE01")
        rows.append({"model": item.get("model"), "track": item.get("track"), "test_id": item.get("test_id"), "recorded_status": status, "legacy_score": item.get("score"), "derived_completion_class": classification, "revised_code_policy": revised, "revised_safe_score": revised_score, "derived_code_status": revised_status if item.get("test_id") == "code_bugfix" and answer else "", "done_reason": done_reason or "", "response_chars": len(answer), "thinking_chars": len(item.get("thinking", ""))})
    fields = list(rows[0]) if rows else ["model"]
    with (OUT / "legacy_regrade.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    summary = {"source": str(source.relative_to(ROOT)), "row_count": len(rows), "completion_classes": {}, "code_policy_counts": {}}
    for row in rows:
        summary["completion_classes"][row["derived_completion_class"]] = summary["completion_classes"].get(row["derived_completion_class"], 0) + 1
        if row["test_id"] == "code_bugfix": summary["code_policy_counts"][row["revised_code_policy"]] = summary["code_policy_counts"].get(row["revised_code_policy"], 0) + 1
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "errata.md").write_text("""# 20260730 增量结果 V2 派生审计\n\n本目录只读取并重新解释昨晚结果，未修改 `20260730_incremental`。\n\n- 旧 runner 使用 `num_predict=900`，对 thinking/reasoning 模型可能在最终答案前截断；本表按 `done_reason`、final response 与 thinking 分开标记。\n- 旧代码 grader 使用宿主进程无约束 `exec`，且 AST 规则过严；本次仅记录新的安全策略分类，不执行旧回答。\n- 旧安全赛道固定要求 SAFE/UNSAFE，和 Guardian/ShieldGemma 的 yes/no 语义不一致；V2 使用 adapter 记录原始输出并单独统计 invalid output。\n- 旧 specialist 题量很少，不能代表完整视觉、OCR、工具或安全能力。\n- 旧 planning grader 依赖固定参考时间；V2 规划评分改为结构化约束验证。\n- `legacy_score` 保留原值，V2 派生状态和安全策略独立保存。\n""", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
