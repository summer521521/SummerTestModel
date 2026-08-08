# Future Work / Backlog

This file records ideas found during the audit. Future work requires user review before implementation.

| Item | Motivation | Current status | Possible next step |
| --- | --- | --- | --- |
| V3 benchmark | Major-version redesign and broader task coverage | Not started; explicitly deferred | Review scope, compatibility and migration plan |
| Additional models | Compare future local/cloud/specialist models | Not tested in this snapshot | Add one model with capability detection and a resumable targeted run |
| Fable / Fara / Qianfan OCR / LightOnOCR | Expand document and OCR coverage | Not executed here | Review runtime support and local assets |
| Qwen/Gemma scaling | Study size and quantization effects | No new experiments authorized | Define matched model/digest cohorts |
| GUI Agent / Computer Use | Evaluate interactive agent behavior | Not implemented | Design a safe simulated environment and acceptance criteria |
| Larger long-context tests | Improve context scaling evidence | Current V2 coverage incomplete | Revisit only with stable task/scorer versions |
| Performance benchmark | Separate cold load, hot inference, TTFT and output speed | Existing fields are partial and non-uniform | Define comparable profiles and repetitions |
| Embedding expansion | Add retrieval metrics beyond the historical incremental run | Not part of V2 comprehensive | Review dataset and Recall@k/MRR protocol |
| OCR perturbations | Test noise, rotation, compression and tables | Current assets are small | Add deterministic local perturbation set |
| Statistical/Pareto analysis | Quantify uncertainty and efficiency tradeoffs | Not required for release | Review sample-size and missingness treatment |
| Scoring strategy revisions | Improve semantic/protocol separation further | `v2.2.0-offline` frozen | Propose a new version with migration tests |

No item in this table is implemented by the Stable Snapshot closeout.
