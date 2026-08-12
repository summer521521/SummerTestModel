# SummerTestModel 当前项目任务总账

## 2026-08-12 RC1 当前状态

当前正式开发体系为 **SummerTestModel Benchmark 1.0-rc1**。旧 V1、20260730 incremental 和 V2 Stable Snapshot 均为 `Legacy Experimental Evidence`，保留用于审计，但不继承旧分数、不与 RC1 混榜。

### 已完成

- 本地正式 baseline 已覆盖 39/39 个计划模型，共 1938 条逻辑记录和 1938 份私有 raw；缺失 raw、重复 inference 和未收口基础设施失败均为 0。
- 评分器 `1.0-rc1.1` 已修复 `CORE_PRACT_04` 对对象数组调用 `set()` 的崩溃，三条旧 scoring error 均通过 offline regrade 修复，模型回答未改变、未补跑。
- 云端参考测试独立完成：2 个可用模型 142 条任务记录；3 个服务端 HTTP 410 条目保留为 availability evidence，不作为能力 0 分。
- 已生成独立赛道、性能、失败分类和官方来源映射；没有 overall universal score，specialist 不因不适用赛道扣分。
- 已提供新增单个模型的机械流程：显式指定现有 reference assignment，只跑新 digest，逐题落盘、可 resume、raw 私有、结果追加导出。

### 当前限制

- 这是本机 practical usability snapshot，不是严格控制变量实验。Ollama 版本、量化、digest、机器和运行日期被记录；patch drift 本身不再是 blocker。
- 7 条 absolute timeout、104 条 truncation-related 和 19 条 runtime anomaly 是当前运行事实；不可把它们改写成网络错误。
- Vision/OCR 题量小且评分严格，当前结果标为 experimental。
- 官方 model card 数据和 RC1 采用不同题库、runtime、精度与 scoring，只能作为发布者声明背景，不能数值相减或宣称复现。
- 模型 retention 全部为 `UNASSESSED`，未做 keeper/dominated/淘汰判断。

### 保留与清理

- 必须保留：RC1 private raw/state、sanitized public results、冻结 manifest/private benchmark、inventory、历史 V1/V2 evidence、日志和 handoff。
- 可重建缓存（`__pycache__`、`.pytest_cache`）不纳入 Git；历史 benchmark 和私有 evidence 不因目录大而删除。
- 真正迁移或删除 legacy evidence 仍需用户单独批准，详见 `docs/legacy_cleanup_plan.md`。

---

以下为 V2 收口时的历史审计记录。

## 审计范围

本账基于仓库规则文件、README、`model_report.md`、V1 results、20260730 incremental run、20260731 V2 smoke、20260731 V2 comprehensive、`runs/derived`、runner/scorer/validation scripts、run state/logs/manifests、Git history 和当前工作树整理。历史 raw response 只读保留。

## A. 已完成

- V1 历史七题、70 分体系及其 raw、CSV、XLSX、报告已经存在，继续作为独立历史基线。
- 20260730 incremental run 已有独立目录、raw response、状态映射、CSV、XLSX 和报告；HTTP 410/cloud unavailable 已与能力零分分离。
- V2 runner 已实现独立 run、任务/尝试记录、canonical resolution、原始响应持久化、断点状态、失败隔离、代码安全子进程和验证脚本。
- 20260731 V2 comprehensive 已保存 1974 条尝试记录、1567 条 canonical 逻辑记录；stage2、stage3、stage4 和一次 recovery 成功，后续 recovery 因 Ollama `WinError 10061` 停止。
- 现有 raw evidence 已生成不改 raw 的 `v2.2.0-offline` 派生重评分，包含状态、legacy score、semantic/protocol 字段、安全混淆矩阵、工具参数核验和 OCR 重复退化标记。

## B. 基本完成但需要收尾

- V2 派生 CSV、Markdown 报告、图表和工作簿需要在本次收口后统一校验并纳入发布提交。
- README 和 `model_report.md` 需要明确 V1、增量 run、V2 Stable Snapshot 的边界及当前覆盖限制。
- Git 尚未提交本次 V2 runner、离线评分、报告和文档成果。

## C. 部分完成

- V2 记录覆盖 44 个清单模型中的 33 个，综合 canonical 记录 1567 条；存在 263 条基础设施失败以及截断、运行时错误、策略拒绝等内容状态。
- V2 当前轨道记录为 core 744、reasoning 240、code 240、translation 192、vision 20、OCR 10、safety 8、tool 8 和 runner 9；long-context、embedding、performance 等没有足够已执行记录，不建立伪造的完整榜单。
- specialist 赛道只在适用模型/已有数据范围内展示，不进入普通 Core 总榜。
- V2 smoke 与仓库根部的同名 smoke 目录存在历史差异；本次不删除、不合并、不覆盖，作为待审计历史证据保留。

## D. 当前版本不再继续做

- 不恢复 V2 comprehensive 的中断阶段，不启动 V3，不新增模型推荐、题库或全模型重测。
- 不为 coverage 100% 补跑几十小时；不为 embedding、性能、长上下文或医疗等缺失赛道制造新 raw。
- 更大 OCR、GUI Agent、Computer Use、Pareto/统计扩展和其他研究性设计全部转入 `docs/future_work.md`。

## E. 发布阻塞项

当前唯一需要在发布前完成的阻塞项是：完成派生报告、工作簿、JSON/CSV/XLSX、raw hash、隐私扫描和 Git diff 验证。Ollama 连接拒绝本身不是发布 blocker，因为已有完整错误证据且不会进入能力零分。

## 历史发布判定

本次发布名称为 **SummerTestModel V2 Stable Snapshot**：它是 existing-data-first 的、诚实的部分覆盖快照，不声称永久 benchmark 完成或全模型可比。Future work requires user review before implementation.
