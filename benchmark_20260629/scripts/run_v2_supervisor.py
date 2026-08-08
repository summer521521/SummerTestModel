"""Sequential unattended supervisor for V2 stages 2-7."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

from benchmark_v2 import ROOT, read_jsonl


RUN = ROOT / "benchmark_20260629" / "runs" / "20260731_v2_comprehensive"
SCRIPT = ROOT / "benchmark_20260629" / "scripts" / "benchmark_v2.py"


def write_state(state):
    target = RUN / "supervisor_state.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)


def run_stage(label, stage, models=None):
    logs = RUN / "logs"; logs.mkdir(parents=True, exist_ok=True)
    out = (logs / f"{label}.out.log").open("a", encoding="utf-8")
    err = (logs / f"{label}.err.log").open("a", encoding="utf-8")
    args = [sys.executable, "-u", str(SCRIPT), "--run-dir", str(RUN), "--stage", str(stage)]
    if models: args += ["--models", *models]
    code = 1
    for attempt in range(1, 4):
        out.write(f"[supervisor] {label} attempt {attempt}/3\n")
        out.flush()
        proc = subprocess.Popen(args, cwd=ROOT, stdout=out, stderr=err)
        code = proc.wait()
        if code == 0:
            break
        out.write(f"[supervisor] {label} attempt {attempt} exited {code}; retrying after 10s\n")
        out.flush()
        if attempt < 3:
            time.sleep(10)
    out.close(); err.close()
    return code


def top_local_models():
    manifest = json.loads((RUN / "model_manifest.json").read_text(encoding="utf-8"))
    names = {m["name"] for m in manifest if not (m["name"].endswith(":cloud") or "-cloud" in m["name"])}
    totals = defaultdict(lambda: [0, 0])
    for row in read_jsonl(RUN / "results.jsonl"):
        if row.get("track") != "core" or row.get("model") not in names: continue
        if isinstance(row.get("score"), (int, float)):
            totals[row["model"]][0] += row["score"]; totals[row["model"]][1] += row.get("max_score") or 0
    ordered = sorted(((score / maximum if maximum else 0, model) for model, (score, maximum) in totals.items()), reverse=True)
    return [model for _, model in ordered[:5]]


def main():
    previous = RUN / "supervisor_state.json"
    state = json.loads(previous.read_text(encoding="utf-8")) if previous.exists() else {"run_id": RUN.name, "stages": []}
    state["status"] = "running"
    state.pop("paused_after_stage", None)
    write_state(state)

    # Stages 2-4 were durably completed before the interruption.  Their only
    # eligible work now is the bounded retry of transient results.
    completed_labels = {entry.get("label") for entry in state.get("stages", []) if entry.get("exit_code") == 0}
    for label, stage in [("stage3-recovery-1", 3), ("stage3-recovery-2", 3), ("stage4-recovery-1", 4), ("stage4-recovery-2", 4)]:
        if label not in completed_labels:
            code = run_stage(label, stage)
            state["stages"].append({"label": label, "stage": stage, "exit_code": code, "purpose": "retry_retryable_only"}); write_state(state)
            if code != 0: state["status"] = "stage_failed"; write_state(state); return code

    for label, stage, models in [("stage5-specialists", 5, None)]:
        if label in completed_labels:
            continue
        code = run_stage(label, stage, models); state["stages"].append({"label": label, "stage": stage, "exit_code": code}); write_state(state)
        if code != 0: state["status"] = "stage_failed"; write_state(state); return code
    if "stage5-medical-controls" not in completed_labels:
        selected = top_local_models(); state["medical_control_models"] = selected; write_state(state)
        code = run_stage("stage5-medical-controls", 5, selected); state["stages"].append({"label": "stage5-medical-controls", "stage": 5, "models": selected, "exit_code": code}); write_state(state)
        if code != 0: state["status"] = "stage_failed"; write_state(state); return code
    for label, stage in [("stage6", 6), ("stage7", 7)]:
        if label in completed_labels:
            continue
        code = run_stage(label, stage); state["stages"].append({"label": label, "stage": stage, "exit_code": code}); write_state(state)
        if code != 0: state["status"] = "stage_failed"; write_state(state); return code
    state["status"] = "all_stages_finished"; write_state(state); return 0


if __name__ == "__main__": raise SystemExit(main())
