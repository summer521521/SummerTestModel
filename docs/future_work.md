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
| Incremental new models | Keep the local comparison current without rerunning 39 models | Mechanical single-model workflow implemented; no new model selected | User supplies exact model tag and explicit frozen reference assignment |
| Publisher claim refresh | Model cards and official benchmark tables change over time | 39-row source map captured for RC1 | Refresh source metadata when a new model is added or before a new publication snapshot |
| RC1 native-thinking contrast | Some thinking-capable models consumed ordinary-profile budget before a final answer | Current RC1 results preserved | Only run an explicit think-on/off contrast under a separately approved study |
| Targeted stream reproduction | Two DeepSeek-family local artifacts produced non-terminal streams after meaningful output | Raw preserved and scored with anomaly tag | Reproduce a small selected subset only if runtime diagnosis is explicitly requested |

No item in this table is implemented by the Stable Snapshot closeout.
