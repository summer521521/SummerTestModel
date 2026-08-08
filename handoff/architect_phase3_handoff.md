# Architect Phase 3 Handoff — SummerTestModel Benchmark 1.0-rc1

基线：`benchmark-rebuild-prep`，起始 HEAD `083e4e234e64181b0c2c13e1beed5cae9029168e`。

## Frozen scope

- 版本仍为 `1.0-rc1`，scorer version 为 `1.0-rc1`；未升到 `1.0.0`。
- Core：24 scored tasks + 1 diagnostic-only provenance task。
- Reasoning：10；Code：8；Translation：6；Tools：8；Vision：8；OCR：10；Long Context：4；Embedding：12 queries / 24 docs；Safety：20；Medical：6；Performance：microbenchmark only。
- 总任务元数据 118 条，其中 117 scored、1 diagnostic-only。
- 公开 task manifest 只包含 task ID、track/category/profile、scorer ID、hash、asset hash 与 private payload 标记；没有 prompt 或 answer。

## Private package

- Local path：`private_benchmark/1.0-rc1/`
- Git 状态：被 `.gitignore` 忽略，不应上传。
- 内容：tasks、ground_truth、assets、hidden_tests、tool_fixtures、embedding、long_context 与 source archive。
- 文件数：266；package manifest SHA256：`5b0672d727a25687155c11229434eced633e3e8f8347614e52389fc41206f868`。
- Vision/OCR fixtures：确定性 PNG，已生成并纳入 asset hashes。

## Model assignments

| Track | Assigned models |
| --- | ---: |
| core | 29 |
| reasoning | 17 |
| code | 30 |
| translation | 31 |
| tools | 28 |
| vision | 7 |
| ocr | 11 |
| long_context | 28 |
| embedding | 1 |
| safety | 2 |
| medical | 6 |
| performance | 29 |

Assignment validation：39 个本地模型全部至少有一个 formal track；cloud 0 个 formal local track；无 mismatch。Retention 全部 `UNASSESSED`。

## Scorers

已加入不含答案的离线通用 scorer primitives：exact、numeric、sequence/set、JSON semantic/protocol、checklist、reasoning FINAL extraction、CER/repetition、classification metrics、safety parser、tool trace validator、cosine retrieval。scorer 不调用 Ollama、OpenAI、其他 LLM 或 Internet。

测试结果：`tests.test_executor_core` 与 `tests.test_scorers` 共 14 tests，全部通过。覆盖 malformed、fence、CRLF、Unicode、conflicting numeric answer、reasoning explanation、tool parameter mismatch、OCR repetition、safety tags、code harness 与 retrieval。

## Assets and hashes

- Private package manifest 已生成。
- 所有 private files、PNG assets、task payloads 与 ground truths SHA256 已写入 private manifest。
- Public manifests：
  - `config/task_manifest.rc1.public.json`
  - `config/scorer_manifest.rc1.public.json`
  - `config/model_execution_plan.rc1.public.json`

## Doctor and calibration

Doctor 必须为 `NOT_READY`：

- `calibration_approved=false`；Sol Medium 未修改为 true；
- 尚未运行 calibration inference；
- 当前 Ollama healthcheck 不可达时也必须保持 NOT_READY；
- private package、public manifests、模型 digest、profile/retry hashes 必须一致才可继续。

## Security and publication

- 未运行正式 benchmark 或任何正式模型题目。
- 未运行 calibration。
- code harness 保持 AST gate、隔离子进程、`python -I -S`、严格 timeout 和危险 builtins/modules 拦截；仍明确是 restricted benchmark harness，不是 adversarial-grade OS sandbox。
- 对 Git tracked 文件执行了边界感知的 exact-ground-truth leakage scan；无冻结答案泄漏。历史 evidence 未删除或改写。
- 未下载、删除或修改模型 inventory；未修改 retention。

等待 Web GPT-5.6 Sol 审核 Phase 3、确认 calibration，并在后续任务中决定是否授权正式执行。
