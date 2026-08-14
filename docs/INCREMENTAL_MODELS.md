# Incremental model workflow

This workflow adds one newly installed local model to the frozen Benchmark 1.0-rc1 task set without rerunning any existing model.

## Policy

- The user must explicitly name a new exact Ollama tag and one existing local reference model.
- The reference model supplies the frozen track/task assignment. The script does not infer capability from the model name or design new tasks.
- `/api/tags` and `/api/show` must confirm the new model digest and required capabilities.
- The artifact must have a substantive local model file and stay within the frozen `<=10B` total-parameter RC1 scope; cloud/catalog stubs are rejected.
- A model already present in the 39-model baseline is rejected to avoid duplicate inference.
- Each digest is a new revision and gets a distinct ignored directory under `private_runs/`.
- Raw evidence and state remain private and Git-ignored. `finalize` exports a separate sanitized JSONL; it does not rewrite an older public file.
- Retention remains `UNASSESSED`.

## Commands

Inspect the installed artifact:

```powershell
python scripts/incremental_model.py inspect --model "new-model:tag"
```

Prepare and review the inherited task assignment without inference:

```powershell
python scripts/incremental_model.py prepare --model "new-model:tag" --reference-model "existing-model:tag"
```

Run only that model after reviewing the printed plan:

```powershell
python scripts/incremental_model.py run --model "new-model:tag" --reference-model "existing-model:tag" --allow-inference
```

If interrupted, use the exact resume command printed by the runner. Completed logical keys are skipped automatically.

Finalize the named private run:

```powershell
python scripts/incremental_model.py finalize --run-dir "private_runs/incremental_new-model_tag_DIGESTPREFIX"
```

Then regenerate aggregate public tables:

```powershell
python scripts/build_rc1_publication.py
python scripts/build_project_report.py
Push-Location site
npm test
Pop-Location
```

`build_rc1_publication.py` preserves the strict RC1 baseline and cloud reference. `build_project_report.py` rebuilds the bilingual practical report and website dataset from approved sanitized aggregate files. A newly finalized model remains an additive result until the user explicitly approves adding it to the aggregate snapshot; no existing model is rerun automatically.

If an incremental run needs the practical scorer, regrade its existing raw offline and publish a new dated sanitized snapshot. Never copy private prompts, ground truth, answers, state, or raw paths into `public_results/`.

## Choosing a reference

Reference selection is a user/architect decision, not an executor decision. Choose an existing model whose frozen applicable tracks match the new artifact. If Ollama metadata lacks a required capability (for example `vision`, `tools`, `thinking`, or `embedding`), preparation stops instead of silently dropping or adding tracks.
