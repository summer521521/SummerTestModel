"""Collect non-sensitive host/GPU facts for honest performance reporting."""
from __future__ import annotations
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

def main(run_dir: str) -> int:
    run = Path(run_dir); data = {"platform": platform.platform(), "python": sys.version, "processor": platform.processor()}
    nvidia = shutil.which("nvidia-smi")
    if nvidia:
        try:
            out = subprocess.run([nvidia, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"], capture_output=True, text=True, timeout=20)
            data["nvidia_smi"] = {"returncode": out.returncode, "stdout": out.stdout.strip(), "stderr": out.stderr.strip()}
        except Exception as exc: data["nvidia_smi"] = {"error": f"{type(exc).__name__}: {exc}"}
    else: data["nvidia_smi"] = {"available": False}
    (run / "reconnaissance_v2.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[sys.argv.index("--run-dir") + 1]))
