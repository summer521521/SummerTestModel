"""Build derived, non-destructive reports for the 20260730 incremental run."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


CORE_ORDER = ["format_json", "math_reasoning", "long_context", "translation_terms", "anti_hallucination", "code_bugfix", "planning_schedule"]
CORE_LABELS = {"format_json": "格式", "math_reasoning": "数学", "long_context": "检索", "translation_terms": "翻译", "anti_hallucination": "可靠性", "code_bugfix": "代码", "planning_schedule": "规划"}


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def corrected_status(row):
    error = row.get("error", "")
    if row.get("status") == "failed" and "HTTP Error 410" in error:
        return "unavailable"
    return row.get("status", "")


def write_csv(path: Path, rows: list[dict], fields: list[str]):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: row.get(key, "") for key in fields} for row in rows)


def visual_content_ok(row):
    response = (row.get("response") or "").upper()
    if row.get("test_id") == "text_card":
        return int("QX-314" in response and "2026-07-30" in response)
    return int(all(token in response for token in ("ALPHA", "12", "BETA", "7")))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run_dir
    rows = load_jsonl(run_dir / "results.jsonl")
    for row in rows:
        row["derived_status"] = corrected_status(row)

    status_rows = [
        {"model": r.get("model"), "track": r.get("track"), "test_id": r.get("test_id"), "recorded_status": r.get("status"), "derived_status": r["derived_status"], "error": r.get("error", "")}
        for r in rows if r.get("derived_status") != r.get("status")
    ]
    write_csv(run_dir / "status_overrides.csv", status_rows, ["model", "track", "test_id", "recorded_status", "derived_status", "error"])

    core = [r for r in rows if r.get("track") == "core_text"]
    by_model = defaultdict(dict)
    for row in core:
        by_model[row["model"]][row["test_id"]] = row
    validated = []
    for model, tests in by_model.items():
        data = {"model": model, "digest": next(iter(tests.values())).get("digest", "")}
        noncode_score = 0
        noncode_complete = True
        strict_score = 0
        strict_complete = True
        elapsed = []
        status_set = set()
        for test_id in CORE_ORDER:
            row = tests.get(test_id)
            score = row.get("score") if row else None
            data[CORE_LABELS[test_id]] = score if isinstance(score, int) else ""
            status_set.add(row.get("derived_status", "missing") if row else "missing")
            if row and row.get("elapsed_sec") is not None:
                elapsed.append(float(row["elapsed_sec"]))
            if test_id != "code_bugfix":
                if isinstance(score, int): noncode_score += score
                else: noncode_complete = False
            if isinstance(score, int): strict_score += score
            else: strict_complete = False
        data.update({
            "safe_noncode_total": noncode_score if noncode_complete else "",
            "safe_noncode_max": 60,
            "strict_total": strict_score if strict_complete else "",
            "strict_max": 70,
            "avg_elapsed_sec": round(sum(elapsed) / len(elapsed), 3) if elapsed else "",
            "statuses": ";".join(sorted(status_set)),
        })
        validated.append(data)
    validated.sort(key=lambda r: (-(r["safe_noncode_total"] if isinstance(r["safe_noncode_total"], int) else -1), r["model"]))
    for i, row in enumerate([r for r in validated if isinstance(r["safe_noncode_total"], int)], 1):
        row["safe_noncode_rank"] = i
    fields = ["safe_noncode_rank", "model", "digest", "safe_noncode_total", "safe_noncode_max", "strict_total", "strict_max", "格式", "数学", "检索", "翻译", "可靠性", "代码", "规划", "avg_elapsed_sec", "statuses"]
    write_csv(run_dir / "core_validated.csv", validated, fields)

    special = []
    for row in rows:
        track = row.get("track")
        if track == "core_text":
            continue
        item = {"track": track, "model": row.get("model"), "digest": row.get("digest"), "test_id": row.get("test_id"), "recorded_status": row.get("status"), "derived_status": row.get("derived_status"), "recorded_score": row.get("score"), "format_exact": "", "content_correct": "", "interpretation": row.get("note", ""), "elapsed_sec": row.get("elapsed_sec", "")}
        if track in {"vision", "ocr"}:
            item["format_exact"] = int(row.get("score") == 1)
            item["content_correct"] = visual_content_ok(row)
            item["interpretation"] = "content vs exact short-format; raw response retained"
        elif track == "safety":
            answer = (row.get("response") or "").strip().upper()
            if answer in {"YES", "NO"}:
                item["derived_status"] = "invalid_response"
                item["interpretation"] = "YES/NO label is incompatible with requested SAFE/UNSAFE; not treated as capability score"
        special.append(item)
    write_csv(run_dir / "specialist_validated.csv", special, ["track", "model", "digest", "test_id", "recorded_status", "derived_status", "recorded_score", "format_exact", "content_correct", "interpretation", "elapsed_sec"])

    full70 = sorted([r for r in validated if isinstance(r["strict_total"], int)], key=lambda r: (-r["strict_total"], r["avg_elapsed_sec"], r["model"]))
    local60 = [r for r in validated if ":cloud" not in r["model"] and "-cloud" not in r["model"] and isinstance(r["safe_noncode_total"], int)]
    cloud60 = [r for r in validated if (":cloud" in r["model"] or "-cloud" in r["model"]) and isinstance(r["safe_noncode_total"], int)]
    track_groups = defaultdict(list)
    for row in special:
        track_groups[row["track"]].append(row)
    lines = ["# 2026-07-30 无人值守增量评测报告", "", "## 本次运行摘要", "", f"- Run ID：`{run_dir.name}`", f"- 结构化结果：{len(rows)} 条；核心文本记录：{len(core)} 条；专用赛道记录：{len(special)} 条。", "- 当前清单中 5 个 cloud 模型已在所有本地阶段完成后执行。", "- HTTP 410 的 cloud 记录保留原始 `failed` 证据，并在本报告中归为 `unavailable`，不计作能力 0 分。", "- 核心代码题不使用历史 runner 的无约束 `exec`；无法通过 AST 白名单的回答标为 `unsafe_to_execute`，不并入严格 70 分总分。", "", "## 核心文本结果", "", "### 安全可验证的非代码比较（60 分）", "", "| 排名 | 模型 | 非代码分 | 平均秒数 | 状态 |", "| ---: | --- | ---: | ---: | --- |"]
    for item in [r for r in validated if isinstance(r["safe_noncode_total"], int)]:
        lines.append(f"| {item.get('safe_noncode_rank','-')} | `{item['model']}` | {item['safe_noncode_total']}/60 | {item['avg_elapsed_sec']} | {item['statuses']} |")
    lines.extend(["", "### 全 7 题严格可计分结果（70 分）", "", "| 排名 | 模型 | 总分 | 平均秒数 |", "| ---: | --- | ---: | ---: |"])
    for rank, item in enumerate(full70, 1):
        lines.append(f"| {rank} | `{item['model']}` | {item['strict_total']}/70 | {item['avg_elapsed_sec']} |")
    lines.extend(["", "## 专用模型结果", ""])
    for track, values in sorted(track_groups.items()):
        lines.extend([f"### {track}", "", "| 模型 | 项目数 | 可计分正确 | 说明 |", "| --- | ---: | ---: | --- |"])
        grouped = defaultdict(list)
        for value in values: grouped[value["model"]].append(value)
        for model, items in sorted(grouped.items()):
            if track in {"vision", "ocr"}:
                correct = sum(int(x["content_correct"] == 1) for x in items)
                note = f"内容正确 {correct}/{len(items)}；严格格式 {sum(int(x['format_exact'] == 1) for x in items)}/{len(items)}"
            elif track == "safety":
                correct = 0; note = "标签体系不兼容，全部为 invalid_response，不作准确率结论"
            else:
                correct = sum(int(x.get("recorded_score") == 1) for x in items); note = "结构化原始响应见 raw/"
            lines.append(f"| `{model}` | {len(items)} | {correct} | {note} |")
        lines.append("")
    lines.extend(["## Cloud 不可用项", "", "| 模型 | 题数 | 原始错误 |", "| --- | ---: | --- |"])
    unavailable = defaultdict(list)
    for row in rows:
        if row.get("derived_status") == "unavailable": unavailable[row["model"]].append(row)
    for model, items in sorted(unavailable.items()):
        lines.append(f"| `{model}` | {len(items)} | {items[0].get('error','')} |")
    lines.extend(["", "## 可复现说明", "", "- 主 runner：`benchmark_20260629/scripts/incremental_benchmark.py`。", "- 恢复方式：以同一 `--run-dir` 重跑对应 `--phase`；已落盘终态不会重测。", "- 所有请求及原始响应位于 `raw/`，机器、模型 digest 和运行状态位于同级 JSON 文件。", ""])
    (run_dir / "final_report.md").write_text("\n".join(lines), encoding="utf-8")
    summary = {"record_count": len(rows), "core_record_count": len(core), "specialist_record_count": len(special), "strict70_top3": [{"model": r["model"], "score": r["strict_total"]} for r in full70[:3]], "local60_top3": [{"model": r["model"], "score": r["safe_noncode_total"]} for r in local60[:3]], "cloud60_top3": [{"model": r["model"], "score": r["safe_noncode_total"]} for r in cloud60[:3]], "unavailable_models": sorted(unavailable)}
    (run_dir / "run_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
