"""Derive V2 CSVs, reports and reproducible charts from durable JSONL."""
from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from benchmark_v2 import ROOT, canonical_rows, read_jsonl


INFRASTRUCTURE_STATUSES = {
    "network_error", "server_error", "auth_required", "unavailable", "interrupted",
    "timeout_inactivity", "timeout_absolute",
}


def is_score(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def publication_rows(run, attempt_rows):
    """Use the frozen offline regrade when available without mutating raw data."""
    offline = run / "offline_regrade.jsonl"
    if not offline.exists():
        return canonical_rows(attempt_rows), "v2.1.0-legacy", "canonical_results.jsonl"
    rows = []
    for source in read_jsonl(offline):
        row = dict(source)
        row["status"] = row.get("offline_status", row.get("status"))
        score = row.get("offline_score", row.get("score"))
        row["score"] = score if is_score(score) else None
        maximum = row.get("max_score")
        row["normalized_score"] = round(row["score"] / maximum, 4) if is_score(row["score"]) and is_score(maximum) and maximum else None
        row["publication_scorer_version"] = "v2.2.0-offline"
        rows.append(row)
    return rows, "v2.2.0-offline", "offline_regrade.jsonl"


def write_csv(path, rows, fields=None):
    fields = fields or sorted({k for row in rows for k in row})
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)


def fmt(value):
    return "" if value is None else value


def main(run):
    run = Path(run)
    attempt_rows = read_jsonl(run / "results.jsonl")
    rows, scorer_version, derived_source = publication_rows(run, attempt_rows)
    manifest = json.loads((run / "model_manifest.json").read_text(encoding="utf-8"))
    by_track = defaultdict(list)
    for row in rows: by_track[row.get("track", "")].append(row)
    aliases = {"reasoning": "reasoning_scores.csv", "code": "code_scores.csv", "translation": "translation_scores.csv", "long_context": "long_context_scores.csv", "vision": "vision_scores.csv", "ocr": "ocr_scores.csv", "safety": "safety_scores.csv", "tool": "tool_scores.csv", "embedding": "embedding_scores.csv", "performance": "performance.csv", "robustness": "robustness_scores.csv", "medical": "medical_scores.csv"}
    fields = ["model", "local_or_cloud", "profile", "task_id", "status", "score", "max_score", "normalized_score", "wall_seconds", "time_to_first_token", "prompt_eval_count", "eval_count", "output_tokens_per_second", "digest", "legacy_status", "legacy_score", "semantic_score", "protocol_score", "infrastructure_failure", "offline_note", "raw_response_path"]
    for track, name in aliases.items():
        write_csv(run / name, [{k: r.get(k, "") for k in fields} for r in by_track.get(track, [])], fields)
    write_csv(run / "all_results.csv", rows)
    failures = [r for r in rows if r.get("status") not in {"completed", "truncated"} or not is_score(r.get("score"))]
    write_csv(run / "failures.csv", failures)
    manual = [r for r in rows if r.get("status") in {"truncated", "truncated_before_final_answer", "invalid_response", "unsafe_code_detected", "policy_rejected"} or r.get("track") in {"safety", "tool"}]
    write_csv(run / "manual_review_queue.csv", manual)

    planning = [row for row in by_track.get("core", []) if str(row.get("task_id", "")).startswith("PLAN")]
    core = [row for row in by_track.get("core", []) if row not in planning]
    pivot = defaultdict(lambda: {"model": "", "digest": "", "local_or_cloud": "", "profile": "", "completed": 0, "required": 0, "score": 0, "max_score": 0, "wall_seconds": []})
    for r in core:
        p = pivot[(r.get("model"), r.get("profile"))]; p["model"] = r.get("model"); p["profile"] = r.get("profile"); p["digest"] = r.get("digest"); p["local_or_cloud"] = r.get("local_or_cloud"); p["required"] += 1
        if r.get("status") in {"completed", "truncated"}: p["completed"] += 1
        if is_score(r.get("score")):
            p["score"] += 0 if str(r.get("status", "")).startswith("truncated") else r["score"]
            p["max_score"] += r.get("max_score") or 0
        if isinstance(r.get("wall_seconds"), (int, float)): p["wall_seconds"].append(r["wall_seconds"])
    core_rows = []
    for p in pivot.values():
        core_rows.append({"model": p["model"], "profile": p["profile"], "local_or_cloud": p["local_or_cloud"], "digest": p["digest"], "completed_count": p["completed"], "required_count": p["required"], "coverage": round(p["completed"] / p["required"], 4) if p["required"] else 0, "score": p["score"], "max_score": p["max_score"], "normalized_score": round(p["score"] / p["max_score"], 4) if p["max_score"] else None, "avg_wall_seconds": round(sum(p["wall_seconds"]) / len(p["wall_seconds"]), 3) if p["wall_seconds"] else None})
    write_csv(run / "core_scores.csv", core_rows)

    def leaders(track, limit=3, source=None):
        grouped = defaultdict(list)
        for r in (source if source is not None else by_track.get(track, [])):
            grouped[(r.get("model"), r.get("profile"))].append(r)
        out=[]
        for (model, profile), items in grouped.items():
            scored=[r for r in items if is_score(r.get("score"))]
            maximum=sum(r.get("max_score") or 0 for r in scored)
            # OCR semantic overlap remains meaningful even when the same
            # response later degenerates into repetition and is truncated.
            # Completion coverage stays separate so it cannot be read as a
            # fully successful OCR result.
            total=sum(r["score"] if track == "ocr" or not str(r.get("status", "")).startswith("truncated") else 0 for r in scored)
            completed=sum(r.get("status") in {"completed","truncated"} for r in items)
            out.append({"model":model,"profile":profile,"score":total,"max_score":maximum,"coverage":round(completed / len(items), 4) if items else 0,"completed":completed,"required":len(items),"avg_seconds":round(sum(r.get("wall_seconds") or 0 for r in items)/len(items),3) if items else None})
        return sorted(out,key=lambda x:(-(x["score"]/x["max_score"] if x["max_score"] else -1),-x["completed"],x["avg_seconds"] or 10**9,x["model"]))[:limit]

    planning_rows = leaders("planning", limit=10, source=planning)
    write_csv(run / "planning_scores.csv", planning_rows, ["model", "profile", "score", "max_score", "coverage", "completed", "required", "avg_seconds"])
    summary = {"run_id": run.name, "task_version": "20260731.v2", "scorer_version": scorer_version, "derived_source": derived_source, "record_count": len(rows), "attempt_record_count": len(attempt_rows), "model_count": len(manifest), "observed_model_count": len({r.get("model") for r in rows if r.get("model")}), "local_models": sum(not (str(r.get("name", "")).endswith(":cloud") or "-cloud" in str(r.get("name", ""))) for r in manifest), "cloud_models": sum(str(r.get("name", "")).endswith(":cloud") or "-cloud" in str(r.get("name", "")) for r in manifest), "status_counts": dict(Counter(r.get("status") for r in rows)), "infrastructure_failure_count": sum(r.get("status") in INFRASTRUCTURE_STATUSES for r in rows), "scored_record_count": sum(is_score(r.get("score")) for r in rows), "track_counts": {**{k: len(v) for k,v in by_track.items() if k != "core"}, "core": len(core), "planning": len(planning)}, "leaders": {**{track: leaders(track, source=core if track == "core" else None) for track in ("core", "reasoning", "code", "translation", "long_context", "vision", "ocr", "safety", "tool", "embedding", "performance", "robustness")}, "planning": planning_rows}}
    (run / "summary_v2.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines=["# SummerTestModel V2 Stable Snapshot", "", "## 发布范围", "", "- 本报告是现有 raw evidence 的离线收口，不恢复中断的模型运行，也不新增模型或题目。", "- 当前 comprehensive run 为部分覆盖的稳定快照；它不构成全模型统一排名。", "- 原始 `results.jsonl` 与 `raw/` 未被改写。", "", "## 运行摘要", "", f"- Run ID：`{run.name}`", f"- Task version：`{summary['task_version']}`；publication scorer：`{scorer_version}`。", f"- 派生输入：`{derived_source}`；规范化记录 {len(rows)} 条；原始尝试记录 {len(attempt_rows)} 条。", f"- 模型清单：{len(manifest)} 个（本地 {summary['local_models']}，cloud {summary['cloud_models']}）；实际有记录模型 {summary['observed_model_count']} 个。", f"- 可评分记录：{summary['scored_record_count']} 条；基础设施失败：{summary['infrastructure_failure_count']} 条。", f"- 状态计数：{json.dumps(summary['status_counts'], ensure_ascii=False)}。", "- 能力得分分母只包含有离线评分的记录；network/server/timeout 等基础设施失败不计为能力 0 分。", "- 公共核心、规划和专项赛道分别排名，不将不同满分相加。", "- 截断、重复退化、策略拒绝与传输失败分别保留，不归因成知识错误。", ""]
    for label, track in [("公共核心（不含规划）", "core"),("规划", "planning"),("推理扩展", "reasoning"),("代码", "code"),("翻译", "translation"),("长上下文", "long_context"),("视觉", "vision"),("OCR 语义（完成率单列）", "ocr"),("安全", "safety"),("工具", "tool"),("Embedding", "embedding"),("稳定性", "robustness")]:
        lines += [f"## {label}榜", "", "| 排名 | 模型 | profile | score | coverage | completed | 平均秒 |", "| ---: | --- | --- | ---: | ---: | ---: | ---: |"]
        for i, item in enumerate(summary["leaders"].get(track, []), 1): lines.append(f"| {i} | `{item['model']}` | `{item['profile']}` | {item['score']}/{item['max_score']} | {item['coverage']:.1%} | {item['completed']}/{item['required']} | {item['avg_seconds']} |")
        if not summary["leaders"].get(track): lines.append("| - | 无适用终态 | - | - | 0 | 0 | - |")
        lines.append("")
    lines += ["## 失败与人工复核", "", f"- failures.csv：{len(failures)} 条，其中基础设施类别见 `infrastructure_failure` 字段。", f"- manual_review_queue.csv：{len(manual)} 条。", "- `offline_regrade.csv` 同时保留 legacy 与 publication 派生状态/分数，可逐条追溯。", "- 完整请求、thinking、最终回答、Ollama 性能字段和 raw hash 保存在 JSONL/raw。", "", "## 已知限制", "", "- stage3-recovery-2 在 Ollama `WinError 10061` 后停止；未自动恢复，以免将基础设施故障伪装成新能力数据。", "- 后续 comprehensive 专项、医疗、性能和 cloud 阶段未完成，相关赛道仅在已有数据足够时展示。", "- OCR 同时报出文本语义、重复退化和截断；不得把截断重复输出解释为完美 OCR。", "", "## 可复现", "", "- Runner：`benchmark_20260629/scripts/benchmark_v2.py`。", "- 离线重评分：`benchmark_20260629/scripts/regrade_v2_offline.py`；原始回答不变。", "- 任务与评分器版本见 `task_manifest.json`、`scorer_manifest.json`、`offline_regrade_summary.json`。", "- 同一 `--run-dir` 重跑对应 stage 会跳过已有终态主键；本快照不要求恢复中断运行。", ""]
    (run / "final_report.md").write_text("\n".join(lines), encoding="utf-8")
    (run / "report.md").write_text("\n".join(lines), encoding="utf-8")

    charts=run/"charts"; charts.mkdir(exist_ok=True)
    try:
        import numpy as np
        import matplotlib.pyplot as plt

        generated = []
        def save(fig, name):
            fig.tight_layout(); fig.savefig(charts / name, format="svg"); plt.close(fig); generated.append(name)
        def normalized(items):
            vals = [r.get("score") / r.get("max_score") for r in items if isinstance(r.get("score"), (int, float)) and r.get("max_score")]
            return sum(vals) / len(vals) if vals else None
        model_info = {m.get("name"): m for m in manifest}
        names=[x["model"] for x in summary["leaders"].get("core", [])]; vals=[x["score"]/x["max_score"]*100 if x["max_score"] else 0 for x in summary["leaders"].get("core", [])]
        fig, ax = plt.subplots(figsize=(9,4)); ax.barh(names[::-1], vals[::-1], color="#2563eb"); ax.set_xlabel("normalized score (%)"); ax.set_title("V2 Core leaders"); save(fig, "core_leaders.svg")
        counts=summary["status_counts"]; fig, ax = plt.subplots(figsize=(7,4)); ax.bar(list(counts),list(counts.values()),color="#64748b"); ax.tick_params(axis="x",rotation=35); ax.set_title("V2 terminal statuses"); save(fig, "status_counts.svg")
        tracks=list(summary["track_counts"]); values=[summary["track_counts"][x] for x in tracks]; fig, ax = plt.subplots(figsize=(9,4)); ax.bar(tracks,values,color="#0f766e"); ax.tick_params(axis="x",rotation=35); ax.set_title("Records by track"); save(fig, "track_records.svg")

        # Core task heatmap: blank cells are not converted into zeroes.
        heat_models = sorted({r.get("model") for r in core if r.get("model")})
        heat_tasks = sorted({r.get("task_id") for r in core if r.get("task_id")})
        if heat_models and heat_tasks:
            matrix = np.full((len(heat_models), len(heat_tasks)), np.nan)
            mi, ti = {x:i for i,x in enumerate(heat_models)}, {x:i for i,x in enumerate(heat_tasks)}
            for r in core:
                if isinstance(r.get("score"), (int, float)) and r.get("max_score"):
                    matrix[mi[r["model"]], ti[r["task_id"]]] = r["score"] / r["max_score"]
            fig, ax = plt.subplots(figsize=(max(10, len(heat_tasks)*.42), max(5, len(heat_models)*.24)))
            im=ax.imshow(matrix, aspect="auto", vmin=0, vmax=1, cmap="YlGnBu"); ax.set_yticks(range(len(heat_models)), [str(x)[:28] for x in heat_models], fontsize=7); ax.set_xticks(range(len(heat_tasks)), heat_tasks, rotation=70, ha="right", fontsize=7); ax.set_title("Core normalized score by model and task"); fig.colorbar(im, ax=ax, label="normalized score"); save(fig, "core_heatmap.svg")

        def aggregate(track):
            grouped=defaultdict(list)
            for r in by_track.get(track, []): grouped[r.get("model")].append(r)
            return {m: normalized(v) for m,v in grouped.items() if normalized(v) is not None}
        core_avg, speed_avg = aggregate("core"), {}
        for r in core:
            if isinstance(r.get("output_tokens_per_second"), (int,float)): speed_avg.setdefault(r.get("model"), []).append(r["output_tokens_per_second"])
        for m in list(speed_avg): speed_avg[m] = sum(speed_avg[m]) / len(speed_avg[m])
        xs=[speed_avg[m] for m in core_avg if m in speed_avg]; ys=[core_avg[m]*100 for m in core_avg if m in speed_avg]
        if xs:
            fig, ax=plt.subplots(figsize=(7,4)); ax.scatter(xs,ys,c="#7c3aed");
            for m in core_avg:
                if m in speed_avg: ax.annotate(str(m)[:18], (speed_avg[m], core_avg[m]*100), fontsize=6)
            ax.set_xlabel("average output tokens/s"); ax.set_ylabel("core normalized score (%)"); ax.set_title("Core score vs output speed"); save(fig,"core_score_vs_speed.svg")
        sx=[(model_info[m].get("size") or 0)/1e9 for m in core_avg if m in model_info and model_info[m].get("size")]; sy=[core_avg[m]*100 for m in core_avg if m in model_info and model_info[m].get("size")]
        if sx:
            fig, ax=plt.subplots(figsize=(7,4)); ax.scatter(sx,sy,c="#ea580c"); ax.set_xlabel("model size (GB)"); ax.set_ylabel("core normalized score (%)"); ax.set_title("Core score vs model size"); save(fig,"core_score_vs_size.svg")

        reason = by_track.get("reasoning", []); rx, ry = [], []
        for r in reason:
            if isinstance(r.get("score"), (int,float)) and r.get("max_score") and isinstance(r.get("eval_count"), (int,float)):
                rx.append(r["eval_count"]); ry.append(r["score"] / r["max_score"] * 100)
        if rx:
            fig, ax=plt.subplots(figsize=(7,4)); ax.scatter(rx,ry,c="#0891b2"); ax.set_xlabel("generated/eval tokens"); ax.set_ylabel("normalized score (%)"); ax.set_title("Reasoning score vs thinking tokens"); save(fig,"reasoning_score_vs_tokens.svg")
        context = by_track.get("long_context", []); cx, cy = [], []
        for r in context:
            if isinstance(r.get("score"), (int,float)) and r.get("max_score") and isinstance(r.get("prompt_eval_count"), (int,float)):
                cx.append(r["prompt_eval_count"]); cy.append(r["score"] / r["max_score"] * 100)
        if cx:
            fig, ax=plt.subplots(figsize=(7,4)); ax.scatter(cx,cy,c="#16a34a"); ax.set_xlabel("prompt eval tokens"); ax.set_ylabel("normalized score (%)"); ax.set_title("Long-context score vs prompt length"); save(fig,"long_context_score_vs_prompt_tokens.svg")
        code = by_track.get("code", []); cgroup=defaultdict(list)
        for r in code:
            if isinstance(r.get("score"), (int,float)) and r.get("max_score"): cgroup[r.get("model")].append(r["score"] >= r["max_score"])
        cp=sorted(((m, sum(v)/len(v)*100) for m,v in cgroup.items() if v), key=lambda x:-x[1])[:20]
        if cp:
            fig, ax=plt.subplots(figsize=(9,5)); ax.bar([str(m)[:22] for m,_ in cp], [v for _,v in cp], color="#9333ea"); ax.tick_params(axis="x",rotation=65); ax.set_ylabel("pass@1 proxy (%)"); ax.set_title("Code pass@1 proxy by model"); save(fig,"code_pass_at_1.svg")
        specialist_tracks=["translation","medical","vision","ocr","safety","tool","embedding"]; sp=[]
        for t in specialist_tracks:
            v=normalized(by_track.get(t, []));
            if v is not None: sp.append((t,v*100))
        if sp:
            fig, ax=plt.subplots(figsize=(8,4)); ax.bar([x for x,_ in sp],[y for _,y in sp],color="#be123c"); ax.set_ylabel("mean normalized score (%)"); ax.set_title("Specialist track comparison"); save(fig,"specialist_track_means.svg")
        perf=defaultdict(list)
        for r in by_track.get("performance", []):
            if isinstance(r.get("output_tokens_per_second"), (int,float)): perf[r.get("task_id")].append(r["output_tokens_per_second"])
        if perf:
            labels=sorted(perf); fig, ax=plt.subplots(figsize=(7,4)); ax.bar(labels,[sum(perf[x])/len(perf[x]) for x in labels],color="#0f766e"); ax.set_ylabel("output tokens/s"); ax.set_title("Cold/hot performance probes"); save(fig,"performance_cold_hot.svg")
        pareto=[(core_avg[m]*100, (model_info[m].get("size") or 0)/1e9, speed_avg.get(m)) for m in core_avg if m in model_info and model_info[m].get("size")]
        if pareto:
            fig, ax=plt.subplots(figsize=(7,4)); ax.scatter([x[1] for x in pareto],[x[0] for x in pareto],c=[x[2] or 0 for x in pareto],cmap="viridis"); ax.set_xlabel("model size (GB)"); ax.set_ylabel("core normalized score (%)"); ax.set_title("Local core score Pareto view (color=speed)"); save(fig,"local_pareto_score_size_speed.svg")
        (charts/"chart_manifest.json").write_text(json.dumps({"generated_by":"finalize_v2.py","charts":generated},indent=2)+"\n",encoding="utf-8")
    except Exception as exc:
        (charts/"chart_error.txt").write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))


if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument("--run-dir",required=True); args=parser.parse_args(); main(args.run_dir)
