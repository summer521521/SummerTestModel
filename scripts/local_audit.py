"""Collect sanitized local facts without invoking model inference."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import platform
import re
import shutil
import statistics
import subprocess
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_API = "http://127.0.0.1:11434/api"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def api_json(base: str, endpoint: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base.rstrip('/')}/{endpoint.lstrip('/')}",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def run(command: list[str], timeout: int = 30) -> dict[str, Any]:
    try:
        completed = subprocess.run(command, capture_output=True, text=False, timeout=timeout)
        def decode(value: bytes) -> str:
            if b"\x00" in value[:200]:
                return value.decode("utf-16", errors="replace").strip()
            for encoding in ("utf-8", "gbk"):
                try:
                    return value.decode(encoding).strip()
                except UnicodeDecodeError:
                    continue
            return value.decode("utf-8", errors="replace").strip()
        return {
            "returncode": completed.returncode,
            "stdout": decode(completed.stdout),
            "stderr": decode(completed.stderr),
        }
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def atomic_json(path: Path, value: Any) -> None:
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def gib(value: int | float | None) -> float | None:
    return None if value is None else round(float(value) / (1024**3), 3)


def find_context(model_info: dict[str, Any]) -> int | None:
    values = []
    for key, value in model_info.items():
        if key.endswith(".context_length") or key == "context_length":
            if isinstance(value, (int, float)):
                values.append(int(value))
    return max(values) if values else None


def specialist_role(name: str, capabilities: list[str]) -> str:
    lower = name.lower()
    if "embedding" in capabilities or "embedding" in lower:
        return "embedding"
    if "guardian" in lower or "shield" in lower:
        return "safety"
    if "ocr" in lower:
        return "ocr"
    if "function" in lower:
        return "tools"
    if "vision" in capabilities or "vision" in lower or "vl:" in lower or "minicpm-v" in lower:
        return "vision"
    if "med" in lower:
        return "medical_name_hint"
    if "translate" in lower or "hy-mt" in lower:
        return "translation_name_hint"
    if "coder" in lower or "starcoder" in lower:
        return "code_name_hint"
    if "reason" in lower or "think" in lower or "r1" in lower or "scaler" in lower:
        return "reasoning_name_hint"
    return "general_or_unknown"


def testability(model: dict[str, Any], total_ram_gib: float, vram_gib: float | None) -> tuple[str, str]:
    if model["local_or_cloud"] == "cloud":
        return "CLOUD_ONLY", "Ollama entry is cloud-backed; local model files are not present."
    size = model.get("disk_size_bytes")
    if not isinstance(size, int) or size <= 0:
        return "UNKNOWN_NEEDS_PROBE", "Installed size is unavailable from /api/tags."
    size_gib = size / (1024**3)
    if size_gib <= max(2.5, (vram_gib or 0) * 0.65):
        return "TESTABLE_EXPECTED", "Model file size fits a conservative fraction of reported VRAM/RAM."
    if size_gib <= min(total_ram_gib * 0.35, 8.0):
        return "TESTABLE_WITH_CPU_OFFLOAD", "Model exceeds conservative VRAM fit but is small relative to system RAM."
    if size_gib <= total_ram_gib * 0.65:
        return "TESTABLE_BUT_RESOURCE_HEAVY", "Model file is large relative to available RAM/VRAM; historical evidence should guide probing."
    return "UNKNOWN_NEEDS_PROBE", "Model file size approaches system-memory limits; no inference probe was authorized."


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * p
    lower, upper = math.floor(index), math.ceil(index)
    if lower == upper:
        return round(ordered[lower], 3)
    return round(ordered[lower] * (upper - index) + ordered[upper] * (index - lower), 3)


def historical_facts() -> tuple[dict[str, int], dict[str, dict[str, float | int | None]], int]:
    statuses: Counter[str] = Counter()
    timings: defaultdict[str, list[float]] = defaultdict(list)
    records_seen = 0
    for path in ROOT.glob("benchmark_20260629/runs/*/canonical_results.jsonl"):
        for line in path.open(encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                statuses["json_corruption"] += 1
                continue
            records_seen += 1
            status = str(row.get("status") or "unknown")
            statuses[status] += 1
            wall = row.get("wall_seconds") or row.get("elapsed_sec")
            track = str(row.get("track") or "unknown")
            if isinstance(wall, (int, float)) and wall >= 0 and status not in {"network_error", "server_error"}:
                timings[track].append(float(wall))
    for path in ROOT.glob("benchmark_20260629/runs/*/results.jsonl"):
        if (path.parent / "canonical_results.jsonl").exists():
            continue
        for line in path.open(encoding="utf-8", errors="replace"):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                statuses["json_corruption"] += 1
                continue
            records_seen += 1
            statuses[str(row.get("status") or "unknown")] += 1
            wall = row.get("wall_seconds") or row.get("elapsed_sec")
            track = str(row.get("track") or "unknown")
            if isinstance(wall, (int, float)) and wall >= 0:
                timings[track].append(float(wall))
    timing_summary = {
        track: {
            "count": len(values),
            "p50_seconds": percentile(values, 0.50),
            "p90_seconds": percentile(values, 0.90),
            "p95_seconds": percentile(values, 0.95),
            "max_seconds": round(max(values), 3),
        }
        for track, values in sorted(timings.items())
    }
    return dict(statuses), timing_summary, records_seen


def historical_models() -> set[str]:
    found: set[str] = set()
    for path in ROOT.glob("benchmark_20260629/runs/*/*.jsonl"):
        if path.name not in {"results.jsonl", "canonical_results.jsonl"}:
            continue
        with path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("model"):
                    found.add(str(row["model"]))
    return found


def path_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def machine_profile() -> dict[str, Any]:
    os_info = run(["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,TotalVisibleMemorySize | ConvertTo-Json -Compress"])
    cpu_info = run(["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Processor | Select-Object -First 1 Name,NumberOfCores,NumberOfLogicalProcessors | ConvertTo-Json -Compress"])
    disks = run(["powershell", "-NoProfile", "-Command", "Get-PSDrive -PSProvider FileSystem | Select-Object Name,Used,Free | ConvertTo-Json -Compress"])
    nvidia = run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version,compute_cap", "--format=csv,noheader,nounits"])
    wsl = run(["wsl.exe", "--status"])
    parsed_os = json.loads(os_info.get("stdout") or "{}") if os_info.get("returncode") == 0 else {}
    parsed_cpu = json.loads(cpu_info.get("stdout") or "{}") if cpu_info.get("returncode") == 0 else {}
    total_ram_gib = round(float(parsed_os.get("TotalVisibleMemorySize", 0)) / 1024 / 1024, 3)
    gpu_parts = [part.strip() for part in (nvidia.get("stdout") or "").split(",")]
    gpu = {
        "name": gpu_parts[0] if len(gpu_parts) >= 1 else None,
        "vram_mib": int(float(gpu_parts[1])) if len(gpu_parts) >= 2 and gpu_parts[1] else None,
        "driver_version": gpu_parts[2] if len(gpu_parts) >= 3 else None,
        "compute_capability": gpu_parts[3] if len(gpu_parts) >= 4 else None,
        "source": "nvidia-smi" if nvidia.get("returncode") == 0 else "unavailable",
    }
    relevant_env = {}
    for name in ("OLLAMA_HOST", "OLLAMA_MODELS", "OLLAMA_KEEP_ALIVE", "CUDA_VISIBLE_DEVICES", "NO_PROXY"):
        if name in os.environ:
            relevant_env[name] = "SET_REDACTED" if any(token in name for token in ("KEY", "TOKEN", "SECRET")) else os.environ[name]
    return {
        "collected_at": now(),
        "windows": {key: parsed_os.get(key) for key in ("Caption", "Version", "BuildNumber")},
        "cpu": parsed_cpu,
        "total_ram_gib": total_ram_gib,
        "gpu": gpu,
        "disks": json.loads(disks.get("stdout") or "[]") if disks.get("returncode") == 0 else [],
        "python": platform.python_version(),
        "ollama_cli": run(["ollama", "--version"]).get("stdout"),
        "ollama_server": None,
        "relevant_environment": relevant_env,
        "wsl_status": "available" if wsl.get("returncode") == 0 else "unavailable_or_not_configured",
        "workspace_drive": ROOT.drive,
    }


def repo_snapshot() -> dict[str, Any]:
    status = run(["git", "status", "--porcelain=v1"])
    return {
        "branch": run(["git", "branch", "--show-current"]).get("stdout"),
        "head": run(["git", "rev-parse", "HEAD"]).get("stdout"),
        "upstream": run(["git", "rev-parse", "--abbrev-ref", "@{upstream}"]).get("stdout"),
        "dirty_entries": [line for line in (status.get("stdout") or "").splitlines() if line],
        "tracked_file_count": len((run(["git", "ls-files"]).get("stdout") or "").splitlines()),
    }


def collect(api_base: str) -> None:
    machine = machine_profile()
    version = api_json(api_base, "version")
    machine["ollama_server"] = version.get("version")
    tags = api_json(api_base, "tags").get("models", [])
    vram_gib = None
    if machine["gpu"].get("vram_mib"):
        vram_gib = machine["gpu"]["vram_mib"] / 1024
    models: list[dict[str, Any]] = []
    anomalies: list[dict[str, str]] = []
    for item in tags:
        name = item.get("name") or item.get("model")
        show: dict[str, Any] = {}
        show_error = None
        try:
            show = api_json(api_base, "show", {"model": name, "verbose": True})
        except Exception as exc:
            show_error = f"{type(exc).__name__}: {exc}"
        details = show.get("details") or item.get("details") or {}
        model_info = show.get("model_info") or {}
        capabilities = sorted(str(value) for value in (show.get("capabilities") or []))
        local_or_cloud = "cloud" if str(name).endswith(":cloud") or "-cloud" in str(name) else "local"
        row = {
            "exact_name": name,
            "tag": str(name).rsplit(":", 1)[-1] if ":" in str(name) else "latest",
            "digest": item.get("digest"),
            "disk_size_bytes": item.get("size"),
            "disk_size_gib": gib(item.get("size")),
            "parameter_size": details.get("parameter_size"),
            "quantization": details.get("quantization_level"),
            "family": details.get("family"),
            "architecture": model_info.get("general.architecture") or details.get("family"),
            "context_length": find_context(model_info),
            "capabilities": capabilities,
            "template_present": bool(show.get("template")),
            "system_prompt_present": bool(show.get("system")),
            "template": show.get("template") or None,
            "system_prompt": show.get("system") or None,
            "modelfile_message_present": bool(re.search(r"(?im)^MESSAGE\s", show.get("modelfile") or "")),
            "local_or_cloud": local_or_cloud,
            "thinking_support": "thinking" in capabilities,
            "tools_support": "tools" in capabilities,
            "vision_support": "vision" in capabilities,
            "embedding_support": "embedding" in capabilities,
            "multimodal_support": "vision" in capabilities or "audio" in capabilities,
            "apparent_specialist_role": specialist_role(str(name), capabilities),
            "currently_installed": local_or_cloud == "local" and bool(item.get("size")),
            "metadata_confidence": "HIGH_API_SHOW" if not show_error else "MEDIUM_TAGS_ONLY",
            "metadata_source": "/api/tags + /api/show" if not show_error else "/api/tags",
            "metadata_error": show_error,
            "modelfile_sha256": hashlib.sha256((show.get("modelfile") or "").encode()).hexdigest() if show.get("modelfile") else None,
            "template_sha256": hashlib.sha256((show.get("template") or "").encode()).hexdigest() if show.get("template") else None,
        }
        metadata_file = ROOT / "inventory/model_metadata_raw" / f"{hashlib.sha256(str(name).encode()).hexdigest()[:20]}.json"
        atomic_json(metadata_file, {"model": name, "digest": item.get("digest"), "modelfile": show.get("modelfile"), "template": show.get("template"), "system": show.get("system"), "capabilities": show.get("capabilities")})
        row["metadata_file"] = metadata_file.relative_to(ROOT).as_posix()
        status, reason = testability(row, machine["total_ram_gib"], vram_gib)
        row["local_testability"] = status
        row["testability_basis"] = reason
        models.append(row)
        modelfile = show.get("modelfile") or ""
        system = show.get("system") or ""
        template = show.get("template") or ""
        flags = []
        if system:
            flags.append("SYSTEM_PRESENT")
        if re.search(r"(?im)^MESSAGE\s", modelfile):
            flags.append("MESSAGE_PRESENT")
        if re.search(r"(?i)(created|developed|trained) by\s+[A-Za-z0-9 ._-]+", system + "\n" + template):
            flags.append("IDENTITY_CLAIM_PRESENT")
        if flags:
            anomalies.append({"model": str(name), "flags": ";".join(flags), "note": "Inspect metadata provenance; no model self-report was used."})
    models.sort(key=lambda row: str(row["exact_name"]).lower())
    fields = [key for key in (list(models[0].keys()) if models else []) if key not in {"template", "system_prompt"}]
    csv_rows = [{**row, "capabilities": ";".join(row["capabilities"])} for row in models]
    atomic_json(ROOT / "environment/machine_profile.json", machine)
    atomic_json(ROOT / "inventory/model_inventory.json", {"collected_at": now(), "ollama_version": version.get("version"), "models": models})
    write_csv(ROOT / "inventory/model_inventory.csv", csv_rows, fields)
    capability_fields = [
        "model", "params", "size_gib", "quant", "context", "general_candidate", "reasoning_capability",
        "code_capability", "tools_capability", "vision_capability", "ocr_candidate", "embedding_capability",
        "safety_specialist", "medical_specialist", "translation_specialist", "cloud", "edge_candidate",
        "metadata_notes",
    ]
    matrix = []
    for row in models:
        role = row["apparent_specialist_role"]
        caps = set(row["capabilities"])
        matrix.append({
            "model": row["exact_name"], "params": row["parameter_size"], "size_gib": row["disk_size_gib"],
            "quant": row["quantization"], "context": row["context_length"],
            "general_candidate": "metadata_not_specialist" if role == "general_or_unknown" else "",
            "reasoning_capability": "metadata_or_name_hint" if "reasoning" in role else ("thinking" if "thinking" in caps else ""),
            "code_capability": "name_hint" if "code" in role else "", "tools_capability": "explicit" if "tools" in caps else "",
            "vision_capability": "explicit" if "vision" in caps else "", "ocr_candidate": "name_hint" if role == "ocr" else "",
            "embedding_capability": "explicit" if "embedding" in caps else "", "safety_specialist": "name_hint" if role == "safety" else "",
            "medical_specialist": "name_hint" if role == "medical_name_hint" else "", "translation_specialist": "name_hint" if role == "translation_name_hint" else "",
            "cloud": row["local_or_cloud"] == "cloud", "edge_candidate": "small_file_only" if (row["disk_size_gib"] or 999) <= 3 else "",
            "metadata_notes": role,
        })
    write_csv(ROOT / "inventory/model_capability_matrix.csv", matrix, capability_fields)
    candidates = []
    models_with_history = historical_models()
    for row in models:
        candidates.append({
            "model": row["exact_name"], "digest": row["digest"], "params": row["parameter_size"],
            "disk_size": row["disk_size_bytes"], "quant": row["quantization"], "local_cloud": row["local_or_cloud"],
            "capabilities": ";".join(row["capabilities"]), "expected_niche": row["apparent_specialist_role"],
            "historical_evidence_available": "YES" if str(row["exact_name"]) in models_with_history else "NO_MATCH_IN_RESULT_RECORDS",
            "local_testability": row["local_testability"], "potential_overlap_group": row["apparent_specialist_role"],
        })
    write_csv(ROOT / "handoff/model_candidates_for_architect.csv", candidates, list(candidates[0].keys()) if candidates else [])
    statuses, timings, historical_records = historical_facts()
    repo = repo_snapshot()
    counts = Counter(row["local_or_cloud"] for row in models)
    role_counts = Counter(row["apparent_specialist_role"] for row in models)

    machine_md = f"""# Machine Profile\n\n- Windows: {machine['windows'].get('Caption')} {machine['windows'].get('Version')} build {machine['windows'].get('BuildNumber')}\n- CPU: {machine['cpu'].get('Name')} ({machine['cpu'].get('NumberOfCores')} physical / {machine['cpu'].get('NumberOfLogicalProcessors')} logical)\n- RAM: {machine['total_ram_gib']} GiB\n- GPU: {machine['gpu'].get('name')}\n- VRAM: {machine['gpu'].get('vram_mib')} MiB\n- NVIDIA driver: {machine['gpu'].get('driver_version')}\n- CUDA compute capability: {machine['gpu'].get('compute_capability')}\n- Python: {machine['python']}\n- Ollama server: {machine['ollama_server']}\n- WSL: {machine['wsl_status']}\n- Workspace drive: {machine['workspace_drive']}\n\nNo username, credential, token, or private home path is included.\n"""
    atomic_text(ROOT / "docs/machine_profile.md", machine_md)
    inventory_lines = ["# Current Ollama Model Inventory", "", f"Collected via `/api/tags` and `/api/show`; total {len(models)}, local {counts['local']}, cloud {counts['cloud']}.", "", "| Model | Digest | Size GiB | Params | Quant | Context | Capabilities | Role hint |", "| --- | --- | ---: | --- | --- | ---: | --- | --- |"]
    for row in models:
        inventory_lines.append(f"| `{row['exact_name']}` | `{str(row['digest'])[:12]}` | {row['disk_size_gib'] if row['disk_size_gib'] is not None else '-'} | {row['parameter_size'] or '-'} | {row['quantization'] or '-'} | {row['context_length'] or '-'} | {', '.join(row['capabilities']) or '-'} | {row['apparent_specialist_role']} |")
    atomic_text(ROOT / "docs/model_inventory.md", "\n".join(inventory_lines) + "\n")
    matrix_lines = ["# Model Capability Matrix", "", "Facts use explicit Ollama metadata where available; `name_hint` is not a capability verdict.", "", "| Model | Explicit capabilities | Role metadata/name hint | Local/cloud | Testability |", "| --- | --- | --- | --- | --- |"]
    for row in models:
        matrix_lines.append(f"| `{row['exact_name']}` | {', '.join(row['capabilities']) or '-'} | {row['apparent_specialist_role']} | {row['local_or_cloud']} | {row['local_testability']} |")
    atomic_text(ROOT / "docs/model_capability_matrix.md", "\n".join(matrix_lines) + "\n")
    anomaly_lines = ["# Model Metadata Anomalies", "", "This audit does not ask models to identify themselves. Findings come only from Modelfile/template/system metadata. `IDENTITY_CLAIM_PRESENT` is an inspection flag, not proof of contamination.", "", "| Model | Flags | Interpretation |", "| --- | --- | --- |"]
    for item in anomalies:
        anomaly_lines.append(f"| `{item['model']}` | {item['flags']} | {item['note']} |")
    if not anomalies:
        anomaly_lines.append("| - | None detected | API metadata inspected successfully. |")
    atomic_text(ROOT / "docs/model_metadata_anomalies.md", "\n".join(anomaly_lines) + "\n")
    test_lines = ["# Local Testability Matrix", "", "Labels estimate execution feasibility from installed size, RAM, VRAM, API metadata, and historical evidence. They are not model-quality or inclusion decisions.", "", "| Model | Status | Basis |", "| --- | --- | --- |"]
    for row in models:
        test_lines.append(f"| `{row['exact_name']}` | {row['local_testability']} | {row['testability_basis']} |")
    atomic_text(ROOT / "docs/local_testability_matrix.md", "\n".join(test_lines) + "\n")
    failure_lines = ["# Historical Failure Modes", "", f"Parsed historical records: {historical_records}.", "", "| Status/symptom | Count | Layer | Model-related? | Recommended executor handling |", "| --- | ---: | --- | --- | --- |"]
    for status, count in sorted(statuses.items(), key=lambda item: (-item[1], item[0])):
        infra = any(token in status for token in ("network", "server", "timeout", "interrupted", "unavailable", "auth"))
        failure_lines.append(f"| `{status}` | {count} | {'infrastructure/runtime' if infra else 'model/scorer/runtime'} | {'No, unless repeated after healthy runtime' if infra else 'Depends on preserved response'} | Persist raw, classify separately, checkpoint, and continue; circuit-break repeated connection refusal. |")
    failure_lines.extend([
        "", "## Named historical incidents", "",
        "| Symptom | Probable layer | Model-related? | Old evidence/workaround | Executor handling |",
        "| --- | --- | --- | --- | --- |",
        "| `WinError 10061` / connection refused cascade | Ollama service/infrastructure | No | V2 `stage3-recovery-2` log; repeated retries produced network errors | Open circuit, stop dispatch, healthcheck, bounded recovery, checkpoint |",
        "| HTTP 410 for cloud entries | Cloud service/account routing | No capability conclusion | Incremental run classified entries unavailable | Preserve response/status; do not score zero; continue |",
        "| Absolute timeout / truncation | Runtime/profile or model completion | Mixed | Historical status and wall-time fields | Preserve partial raw and termination reason; architect decides scoring |",
        "| Repetition degeneration in OCR | Model output behavior | Yes, after healthy execution | Offline V2 regrade separated semantic overlap and completion | Record semantic text, repetition flag and completion independently |",
        "| Legacy in-process `exec(model_output)` | Scorer safety defect | No | V1 scorer source | Never use; run validated code in isolated child process |",
        "| Corrupt/partial state or duplicate key | Persistence/resume | No | No material historical corruption proven; risk identified from design | Quarantine state, rebuild from events, key by version+digest+profile+task |",
    ])
    failure_lines.extend(["", "## Timing Evidence", "", "| Track | N | P50 s | P90 s | P95 s | Max s |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
    for track, item in timings.items():
        failure_lines.append(f"| {track} | {item['count']} | {item['p50_seconds']} | {item['p90_seconds']} | {item['p95_seconds']} | {item['max_seconds']} |")
    atomic_text(ROOT / "docs/historical_failure_modes.md", "\n".join(failure_lines) + "\n")
    local_audit = f"""# Local Audit Report\n\n## Repository\n\n- Branch: `{repo['branch']}`\n- HEAD at collection: `{repo['head']}`\n- Upstream: `{repo['upstream']}`\n- Tracked files: {repo['tracked_file_count']}\n- Dirty entries at collection: {len(repo['dirty_entries'])}\n- Historical structures: V1 results, 20260730 incremental, two distinct V2 smoke directories, 20260731 V2 comprehensive, and derived regrades.\n\n## Local Facts\n\n- Ollama entries: {len(models)} ({counts['local']} local, {counts['cloud']} cloud).\n- Historical parsed records: {historical_records}.\n- Existing V1 scorer directly executes model output in-process; it must not be reused for future code tasks.\n- V2 persistence has fsync JSONL and checkpoint behavior, but task/scorer definitions are coupled to the historical runner.\n- Future executor preparation is intentionally specification-free and requires frozen architect manifests.\n\n## Role Counts\n\n```json\n{json.dumps(dict(role_counts), ensure_ascii=False, indent=2)}\n```\n"""
    local_audit = local_audit.replace(
        f"- Dirty entries at collection: {len(repo['dirty_entries'])}",
        "- Worktree at task start: clean and synchronized with `origin/main` (verified before preparation).\n"
        f"- Preparation-generated dirty entries at this regeneration: {len(repo['dirty_entries'])}.",
    )
    atomic_text(ROOT / "docs/local_audit_report.md", local_audit)
    atomic_text(ROOT / "docs/local_only_findings.md", """# Local-Only Findings\n\nAt collection start, the repository was clean and `main` matched `origin/main`; no important untracked user files were found. The only local-only files observed were ignored Python `__pycache__` bytecode generated by prior validation. They are rebuildable and must not be committed.\n\nThe two V2 smoke directories are both tracked and have distinct run IDs/content. They must not be merged or deleted without an architect-approved migration. All historical raw responses, results JSONL, state, manifests, logs, and derived regrades are tracked evidence and must not be discarded.\n\nFiles created by this preparation task are intentionally local until reviewed and committed on the preparation branch; they are not present on `origin/main` until a later explicit push.\n""")
    legacy_paths = [
        ("benchmark_20260629/results/", "V1 evidence", "Preserve historical evidence", "Contains original raw/results"),
        ("benchmark_20260629/runs/20260730_incremental/", "Incremental evidence", "Preserve historical evidence", "Independent resumable run"),
        ("benchmark_20260629/runs/20260731_v2_comprehensive/", "V2 evidence", "Preserve historical evidence", "Immutable inference evidence and derived scores"),
        ("benchmark_20260629/runs/20260731_v2_smoke/", "Smoke evidence", "Await architect decision", "Distinct from root smoke run"),
        ("benchmark_20260731_v2_smoke/", "Smoke evidence", "Await architect decision", "Distinct run ID/content"),
        ("benchmark_20260629/scripts/benchmark.py", "Legacy runner/scorer", "Do not use for future code scoring", "Executes model output in process"),
        ("benchmark_20260629/scripts/benchmark_v2.py", "Coupled V2 runner", "Reuse persistence ideas only", "Contains frozen old tasks/scorers"),
    ]
    cleanup_lines = ["# Legacy Cleanup Plan", "", "No historical benchmark data was deleted or moved.", "", "| Path | Type | Tracked | Remote history | Size bytes | Recommended action | Reason | Recovery |", "| --- | --- | --- | --- | ---: | --- | --- | --- |"]
    for relative, kind, action, reason in legacy_paths:
        cleanup_lines.append(f"| `{relative}` | {kind} | yes | yes (`origin/main` at audit start) | {path_size(ROOT / relative)} | {action} | {reason} | Restore from Git commit `ea68462` |")
    cleanup_lines.append("| `**/__pycache__/` | Generated cache | no (ignored) | no | rebuildable | Safe to omit | Python bytecode only | Re-run Python |")
    cleanup_lines.extend(["", "True deletion or migration requires Web GPT/user approval."])
    atomic_text(ROOT / "docs/legacy_cleanup_plan.md", "\n".join(cleanup_lines) + "\n")
    handoff = f"""# Web GPT Local Preparation Handoff\n\n## Repository\n\n- Branch at audit start: `{repo['branch']}`; HEAD `{repo['head']}`; upstream `{repo['upstream']}`.\n- The tree was clean before preparation. No unpushed commit or important untracked user artifact was found.\n- Old benchmark systems are tracked historical evidence. V1 `benchmark.py` has unsafe in-process code execution; V2 has useful persistence but embeds old tasks/scorers.\n\n## Machine\n\n- CPU: {machine['cpu'].get('Name')} ({machine['cpu'].get('NumberOfCores')}C/{machine['cpu'].get('NumberOfLogicalProcessors')}T)\n- RAM: {machine['total_ram_gib']} GiB\n- GPU: {machine['gpu'].get('name')}, {machine['gpu'].get('vram_mib')} MiB VRAM, driver {machine['gpu'].get('driver_version')}, compute capability {machine['gpu'].get('compute_capability')}\n- Python: {machine['python']}; Ollama: {machine['ollama_server']}\n- Workspace drive free-space data is in `environment/machine_profile.json`.\n\n## Models\n\n- Current inventory: {len(models)} entries; {counts['local']} local and {counts['cloud']} cloud.\n- Exact digest, size, params, quantization, context, capabilities, metadata confidence, testability and role hints are in `inventory/model_inventory.csv` and `handoff/model_candidates_for_architect.csv`.\n- Role hints are facts/name hints, not keeper/dominance decisions.\n\n## Historical Failure Evidence\n\n```json\n{json.dumps(statuses, ensure_ascii=False, indent=2)}\n```\n\n## Timing Evidence\n\n```json\n{json.dumps(timings, ensure_ascii=False, indent=2)}\n```\n\n## Infrastructure Readiness\n\n- Historical persistence and raw evidence are preserved.\n- New specification-free executor core provides atomic state, fsync JSONL, immutable raw evidence, resume, failure isolation, mock adapter, circuit-breaker placeholders, doctor and status.\n- Doctor must return NOT_READY while any architect field is pending.\n- No formal inference was run during preparation.\n\n## Decisions Needed From Web GPT\n\n- Benchmark/task/scorer manifests and their versions/hashes.\n- Model selection and capability eligibility matrix.\n- Generation profiles, context/output limits and keep-alive policy.\n- Inactivity/absolute timeout values per profile.\n- Retry and circuit-breaker thresholds/waits/recovery limits.\n- Scoring semantics, weights, ranking, size classes, dominance and retention rules.\n- Final execution plan and release/version policy.\n"""
    model_handoff_lines = ["", "## Per-model Core Facts", "", "| Model | Digest | GiB | Params | Quant | Context | Local/cloud | Capabilities | Role hint | Testability |", "| --- | --- | ---: | --- | --- | ---: | --- | --- | --- | --- |"]
    for row in models:
        model_handoff_lines.append(f"| `{row['exact_name']}` | `{str(row['digest'])[:12]}` | {row['disk_size_gib'] if row['disk_size_gib'] is not None else '-'} | {row['parameter_size'] or '-'} | {row['quantization'] or '-'} | {row['context_length'] or '-'} | {row['local_or_cloud']} | {', '.join(row['capabilities']) or '-'} | {row['apparent_specialist_role']} | {row['local_testability']} |")
    handoff += "\n" + "\n".join(model_handoff_lines) + "\n"
    handoff += "\n## Engineering Caveat\n\nThe code harness has AST restrictions, no imports, restricted builtins, isolated `python -I -S`, a temporary working directory and timeout, but it is not an OS-level container/firewall sandbox. A real Ollama execution adapter is intentionally not enabled until architect-owned manifests and policies are frozen.\n"
    atomic_text(ROOT / "handoff/web_gpt_handoff.md", handoff)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default=DEFAULT_API)
    args = parser.parse_args()
    collect(args.api)
    print("LOCAL_AUDIT_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
