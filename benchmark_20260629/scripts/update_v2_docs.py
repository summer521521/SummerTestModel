"""Append a generated V2 section to the project docs without replacing history."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "benchmark_20260629" / "runs" / "20260731_v2_comprehensive"
MARKER = "## 20260731_v2_comprehensive"

def main() -> int:
    summary = json.loads((RUN / "summary_v2.json").read_text(encoding="utf-8"))
    leaders = summary.get("leaders", {})
    lines = [
        MARKER, "", "### V2 Stable Snapshot", "", "本节是基于既有 raw evidence 的离线收口，不恢复中断任务，也不新增模型、题库或全量重测。它与 V1 七题 70 分榜及 20260730 incremental run 独立，三者不能混合排名。", "",
        f"- Task version：`{summary['task_version']}`；publication scorer：`{summary['scorer_version']}`。",
        "- 运行目录：[V2 comprehensive](benchmark_20260629/runs/20260731_v2_comprehensive/)。",
        f"- 清单模型：{summary['model_count']}（本地 {summary['local_models']}，cloud {summary['cloud_models']}）；有实际记录模型：{summary['observed_model_count']}。",
        f"- canonical 记录：{summary['record_count']}；原始尝试：{summary['attempt_record_count']}；可评分：{summary['scored_record_count']}；基础设施失败：{summary['infrastructure_failure_count']}。",
        "- raw response、`results.jsonl` 和 legacy scores 保持不变；`offline_regrade.csv` 并列保存 legacy 与 publication 派生结果。",
        "",
        "### Comparison Boundaries", "",
        "- General/Core、Reasoning、Code、Translation、Vision、OCR、Safety、Tools 分别展示；specialist 不进入普通 Core 总榜。",
        "- 仅有可评分记录进入能力得分分母；network/server/timeout/unavailable 不作为能力 0 分。",
        "- coverage 表示该模型在此赛道已有记录的完成比例，不表示整个模型清单覆盖率。OCR 分数为文本语义重叠，重复退化/截断仍由 coverage 和状态单列。long-context、embedding、performance 与 robustness 没有足够 V2 数据时不建立榜单。",
        "",
        "### Existing-data Results", "", "| 赛道 | 第一名 | 得分 | 已有记录 coverage |", "| --- | --- | ---: | ---: |"]
    for track in ("core", "reasoning", "code", "translation", "long_context", "vision", "ocr", "safety", "tool", "embedding", "performance", "robustness"):
        leader = (leaders.get(track) or [None])[0]
        if leader:
            lines.append(f"| {track} | `{leader['model']}` | {leader['score']}/{leader['max_score']} | {leader['coverage']:.1%} |")
        else:
            lines.append(f"| {track} | 无适用终态 | - | 0 |")
    lines += [
        "", "完整报告：[final_report.md](benchmark_20260629/runs/20260731_v2_comprehensive/final_report.md)；表格：[all_results.csv](benchmark_20260629/runs/20260731_v2_comprehensive/all_results.csv)、[scores.xlsx](benchmark_20260629/runs/20260731_v2_comprehensive/scores.xlsx)；失败分类：[failures.csv](benchmark_20260629/runs/20260731_v2_comprehensive/failures.csv)。",
        "",
        "### Reproduce and Increment", "",
        "1. `ollama pull <model>`，再运行 capability reconnaissance；不要以模型名猜测能力。",
        "2. 只对新模型运行适用赛道，使用独立 run directory，并保留 raw response、digest 与状态。",
        "3. 中断后使用同一 run directory resume；终态记录会被跳过，不能覆盖既有有效结果。",
        "4. 使用 `regrade_v2_offline.py` 和 `finalize_v2.py` 从已有 raw 重新生成派生报告。",
        "5. 只有 benchmark major version、scorer 无法离线重评、Ollama 推理行为发生重大变化或用户明确要求时，才考虑全量重测。",
        "",
        "V2 使用流式响应、每题持久化、独立任务/评分器版本、受限代码子进程和显式 cloud preflight；截断、策略拒绝、不可用与传输失败不混为能力 0 分。已知限制和未来补测见 [docs/current_project_status.md](docs/current_project_status.md) 与 [docs/future_work.md](docs/future_work.md)。", ""]
    block = "\n".join(lines)
    for name in ("README.md", "model_report.md"):
        path = ROOT / name
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        prefix = text.split(MARKER, 1)[0].rstrip()
        path.write_text(prefix + "\n\n" + block + "\n", encoding="utf-8")
    print(json.dumps({"updated": ["README.md", "model_report.md"], "marker": MARKER}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
