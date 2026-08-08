# Architect Handoff — Phase 3R RC1 Freeze Integrity Repair

## Scope and boundary

Phase 3R repaired integrity defects in the existing `1.0-rc1` freeze. It did not run model inference, calibration, benchmark tasks, or a performance microbenchmark. The private task, ground-truth, and scoring payload remains under the ignored local `private_benchmark/1.0-rc1` package; the public repository contains identifiers, categories, scorer IDs, methodology, and hashes only.

`calibration_approved` remains `false`. Model selection, assignments, profiles, timeout/retry policy, prompts, ground truth, retention, and benchmark content were not redesigned.

## Defects found in the pre-repair freeze

The old freeze was invalid for publication and execution because it showed:

- 117 task prompt/ground-truth identity collisions;
- 118 private task/ground-truth payload identity collisions;
- 18 placeholder or invalid-dimension visual/OCR assets;
- 8 CODE tasks without the required structured hidden-test vectors;
- 25 invalid category/profile combinations;
- 13 scorer/schema validation errors.

These figures are preserved as audit evidence; historical raw results were not edited or deleted.

## Repaired freeze

- Public task manifest: 118 tasks; 116 scored, 1 diagnostic-only, 1 telemetry-only.
- Core categories are balanced at four tasks each across extraction, format instruction, logic, arithmetic, practical, and reliability.
- CODE_01 through CODE_08 each have exactly 10 architect-specified hidden-test cases.
- Vision/OCR assets are deterministic local renders at 1024×768; 18 assets are present and no placeholder dimensions remain.
- Long-context payloads contain four generated inputs with exactly one target occurrence each, across the 8K and 32K tiers.
- Embedding fixtures contain 24 corpus documents and 12 queries.
- Safety fixtures contain 10 safe and 10 unsafe cases.
- OCR scoring uses Unicode-normalized Levenshtein distance and reports edit distance, CER, semantic score, repetition, and completion separately.
- Numeric scoring handles a final `FINAL:` line and does not confuse earlier reasoning numbers with the final answer.
- Scoring is dispatched through named deterministic track entrypoints; no LLM judge is used.
- Public manifest and private package hashes are independently checked by doctor.

Current hashes:

| Artifact | SHA-256 |
| --- | --- |
| task manifest | `f4dd76a8ed1448cc1b06358bf5dd26e2c0194625552d9bfe74b564a1f9b9dc0b` |
| scorer manifest | `719380fb0259071f1ff90f02b8463c8ebcfd0dfc391658267c6083c704df8b27` |
| model execution plan | `aea42ee78c0fc429c2e95add04058c8a79ddfbc6682ec17c9e06328c5dd1b1ee` |
| private package manifest | `efe36ac8caf4b57d4e18b472f8145f7ee425bea3e6ed9877e7dee879aaced02e` |
| benchmark manifest | `638113acb55aaff78865adda491078e24551e73eafdd9710244e6d233c75cd5a` |

## Validation evidence

- `python -m py_compile scripts/*.py tests/*.py`: passed.
- `python -m unittest tests.test_phase3r_validator tests.test_scorers tests.test_executor_core -v`: 18 tests passed.
- Public benchmark, task, scorer, and model-plan JSON documents validate against their JSON Schemas.
- `python scripts/phase3r_validator.py`: valid; all six defect metrics are zero.
- `python scripts/luna_executor.py doctor --config config/run_config.template.json`: `NOT_READY` for the intended reasons only: calibration is not approved and Ollama is not reachable. All freeze-integrity, schema, hash, inventory, asset, sandbox, mock, and fixture checks pass.

## Architect decisions still required

Web GPT must still approve the final task/scorer specification and calibration gate before any formal run. It must also decide any future benchmark interpretation, model inclusion beyond the frozen candidate plan, and publication policy. No retention decision has been made; all candidates remain `UNASSESSED`.

## Explicit stop condition

No formal benchmark was run. No model was downloaded or deleted. No Ollama model metadata was changed. No new task was added. No private payload was staged or pushed. Phase 3R is ready for architect review, and execution must stop until Web GPT provides the next authorized specification.
