# SummerTestModel RC1 Baseline Night 3 Handoff

Status: NIGHT3_BLOCKED

Benchmark: 1.0-rc1  
Formal run: `private_runs/rc1_baseline_20260809`  
Branch: `benchmark-rebuild-prep`  
Repository HEAD: `fa03f50b1b7edb682854fb7571859c0700e5957d`  
Main: unchanged at `ea684625749aeafd1709f2d8a113cd268aa3db7d`

## Blocking gate

Night 3 did not start model execution. The frozen preflight requires Ollama 0.32.6, but the installed/running Ollama reports:

    actual version: 0.32.7
    required version: 0.32.6

This is a fail-closed environment/version drift. No downgrade, update, restart loop, model change, or configuration change was attempted.

Ollama API health was HTTP 200, `/api/ps` reported zero active models, and `ollama list` was readable. The version mismatch remains blocking; doctor was not run and no Night 3 model was launched.

## Preserved formal state

Night 1 and Night 2 evidence remains in the same formal run directory. Independent read-only audit before the gate confirmed:

    logical records: 714
    raw records: 714
    score records: 714
    fully accounted models: 19 / 39
    missing raw: 0
    missing score: 0
    duplicate logical keys: 0
    duplicate inference: 0
    partial models: 0

Public result: NOT GENERATED  
Finalization: NOT RUN  
Night 3 models started: 0  
Night 4: NOT RUN

## Isolation and scope

`git ls-files private_benchmark` and `git ls-files private_runs` were empty. No private evidence was staged or published. No cloud benchmark was run. No model was downloaded, deleted, updated, or re-quantized. No benchmark, scorer, assignment, runtime policy, or retention policy was modified.

Retention: UNASSESSED
