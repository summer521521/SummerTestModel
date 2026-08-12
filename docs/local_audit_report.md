# Local Audit Report

## Repository

- Branch: `main`
- HEAD at collection: `ea684625749aeafd1709f2d8a113cd268aa3db7d`
- Upstream: `origin/main`
- Tracked files: 2711
- Worktree at task start: clean and synchronized with `origin/main` (verified before preparation).
- Preparation-generated dirty entries at the final regeneration: 17.
- Historical structures: V1 results, 20260730 incremental, two distinct V2 smoke directories, 20260731 V2 comprehensive, and derived regrades.

## Local Facts

- Ollama entries: 44 (39 local, 5 cloud).
- Historical parsed records: 1856.
- Existing V1 scorer directly executes model output in-process; it must not be reused for future code tasks.
- V2 persistence has fsync JSONL and checkpoint behavior, but task/scorer definitions are coupled to the historical runner.
- Future executor preparation is intentionally specification-free and requires frozen architect manifests.

## Role Counts

```json
{
  "reasoning_name_hint": 5,
  "ocr": 2,
  "general_or_unknown": 19,
  "tools": 1,
  "vision": 10,
  "safety": 2,
  "translation_name_hint": 1,
  "code_name_hint": 3,
  "embedding": 1
}
```
