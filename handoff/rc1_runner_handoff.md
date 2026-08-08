# RC1 Runner Handoff

## rc1_runner commands

`scripts/rc1_runner.py` provides `doctor`, `calibrate`, `run-all`, `resume`, `status`, `finalize`, and `launch`. Real calibration and inference require the explicit `--allow-inference` gate. The offline integration path uses `--mock` and never contacts Ollama.

## Item builder

`RC1ItemBuilder` reads the frozen benchmark, public task/scorer/model manifests, generation profiles, inventory, and the local private package. It constructs identity-complete items from explicit model-plan assignments and inventory capabilities; it does not infer capabilities from model names.

## FormalScorer

`FormalScorer` resolves each task's `scorer_id` through the frozen scorer manifest, loads the corresponding private task, ground truth, and scoring spec, then calls the existing Phase 3S scorer entrypoint in `scripts/scorers.py`. No second scorer implementation was created.

## Tool integration

Formal tool items send Ollama-native function schemas. The bounded loop validates the frozen tool name and argument schema, executes deterministic local fixtures only, appends tool results, and allows at most three assistant rounds. The complete assistant/tool trace and per-turn raw stream evidence are preserved. Mock tests cover chained and zero-call tasks.

## Vision/OCR path

Declared private image assets are hash-validated by doctor, base64 encoded by the item builder, and placed in the user chat message sent to `/api/chat`. The integration test verifies that image bytes are present in the request path, not merely recorded as asset paths.

## Embedding path

Embedding items load the frozen corpus and query, call `/api/embed` separately for corpus and query, retain vectors as private evidence, rank by cosine similarity through the existing Phase 3S embedding scorer, and expose no raw vectors through public finalize output.

## Calibration gate

The fixed calibration plan is in `config/calibration_plan.rc1.json`. Semantic correctness is not a gate. Validation checks runtime path, raw persistence, scorer path, thinking separation, tool loop, image path, embedding path, safety parser, and repeat-resume deduplication. A failed calibration prevents approved-config creation and prevents run-all.

## launch mock test

The mock launch executes doctor -> calibration -> calibration validation -> local ignored approved config -> READY doctor -> representative all-track run -> finalize. It covers text, thinking, code, tool, vision, OCR, embedding, safety, resume, timeout/failure isolation primitives, and public/private separation without model inference.

## Resume

Resume uses the frozen logical identity `(benchmark_version, task_manifest_hash, model_digest, profile, task_id)`. Repeated resume skips terminal inference with saved raw evidence. Scorer errors retain raw evidence for offline regrade, and ordinary task/model failures do not stop subsequent items.

## Private/public isolation

All formal raw evidence defaults to Git-ignored `private_runs/`. `finalize` exports only identity, status, timing, and derived score fields; prompts, answers, streams, thinking, images, tools, and embeddings remain private.

## Tests

- Python compileall: PASS.
- Unit/integration suite: 38/38 PASS.
- Phase 3S golden validation: 116/116 tasks and 80/80 code cases PASS.
- Phase 3R validator: `valid=true`, zero reported errors.
- `git diff --check`: PASS.
- Doctor with the tracked template: `NOT_READY`, as required until real calibration is approved; no inference was initiated.

## Commit SHA

Implementation commit: `6620ba501afcbfe32ff7b43622ba3e09706360a8` (`Wire RC1 formal execution pipeline`).

NO OLLAMA MODEL INFERENCE WAS RUN.

CALIBRATION WAS NOT RUN.

FULL BASELINE WAS NOT RUN.
