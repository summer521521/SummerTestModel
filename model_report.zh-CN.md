# SummerTestModel Benchmark 1.0-rc1 实用模型报告

[简体中文] · [English](model_report.md) · [阶段最终报告](docs/final_report.zh-CN.md) · [双语交互网站](https://summertestmodel-benchmark.walker-ethan.chatgpt.site)

## 范围

本报告描述建立在规范化基线上的当前实用快照：39/39 个本地模型、1,938 条任务记录与对应的 1,938 份本地不可变 raw；严格发布评分器为 `1.0-rc1.1`，实用评分器为 `practical-regrade-1`；8 个模型共 50 条定向恢复全部完成，其中 39 条被实用视图选用。没有缺失 raw、重复 inference key、未解决评分错误或基础设施未完成记录。

原严格基线完全不变。实用分来自已有 raw 的离线重评和明确标注的恢复证据，反映记录的 Windows/Ollama 本机环境中的实际可用性，不是全球模型总榜，也不能与厂商排行榜直接换算。

## 各赛道本地结果

| 赛道 | 本轮领先模型 | RC1 赛道均值 | 说明 |
| --- | --- | ---: | --- |
| Core | Gemma4、Qwen3-8B Q4、Falcon H1R、Ministral3、Qwen3-VL、Qwen3.5 9B | 0.879 | 6 个模型并列 |
| Reasoning | 13 个模型 | 0.800 | 当前夹具不足以区分头部 |
| Code | OLMo Think | 0.900 | 8/8 完成 |
| Translation | Gemma4、Qwen3-8B Q4、Qwen3-VL | 1.000 | 并列 |
| Tools | Qwen3-8B Q4、LFM2.5、MiniCPM v4.6、Qwen3-VL | 0.909 | 并列 |
| Long Context | 23 个模型 | 1.000 | 只有 4 条夹具，区分度低 |
| Embedding | Qwen3 Embedding | 1.000 | 专用赛道 |
| Safety | Granite Guardian 4.1 8B | 1.000 | 专用赛道 |
| Medical | Nemotron 4B、Qwen3.5 4B、Qwen3.5 9B | 0.800 | 应用赛道，不是临床验证 |
| OCR | DeepSeek OCR | 0.792 | 完成率 100%；GLM-OCR 语义 0.810 但完成率 0% |
| Vision | Qwen3-VL 8B | 1.000 | 实验性，只有 8 条夹具 |

完整实用逐模型逐赛道数据见 [`public_results/rc1_practical_track_scores.csv`](public_results/rc1_practical_track_scores.csv)，严格表保留在 [`public_results/rc1_track_scores.csv`](public_results/rc1_track_scores.csv)。性能遥测单独报告，不增加能力分。

## 运行与评分结果

- 定向恢复 50/50 完成，39 条被选用；
- 实用快照中保留 5 次 absolute timeout 与 74 条 truncation-related 记录；
- 6 条恢复后的能力任务仍没有可评分 final；
- 未解决评分错误为 0，基础设施未完成为 0。

三个 `CORE_PRACT_04` 评分器崩溃已在 `1.0-rc1.1` 中修复。实用重评进一步拆分语义、协议、完成、重复退化、工具维度与安全混淆指标。详细分类见[失败分析](docs/rc1_failure_analysis.md)，50 条恢复对照见 [`public_results/rc1_practical_recovery_20260813.csv`](public_results/rc1_practical_recovery_20260813.csv)。

## 云端参考与解释边界

云端评测只用于背景对照，不进入本地基线。`gpt-oss:120b-cloud` 与 `minimax-m3:cloud` 完成 142 条任务；另外三个目录条目返回 HTTP 410，属于服务可用性证据而非能力 0 分。

- 不计算万能总分；
- 专用模型只比较适用赛道；
- Vision/OCR 在 RC1 中为实验性；
- 官方主张只作定位背景，除非数据集、prompt、精度、runtime 与 scorer 全部一致，否则不进行数值等价比较；
- Retention 保持 `UNASSESSED`，用途推荐不等于 dominance 或删除结论。

39 个模型的逐一预期、实际表现、注意事项和使用建议见[阶段最终报告](docs/final_report.zh-CN.md)。

## 后续增量评测

以后新增模型应使用现有增量工作流，只运行适用的冻结赛道，不重跑原来的 39 个模型。每次追加记录 digest 和运行时，私有 raw 保留在本地，只发布脱敏派生结果。见[增量模型流程](docs/INCREMENTAL_MODELS.md)。

旧 V1/V2 结果仅保留作历史审计，不在本报告复述，也不与 Benchmark 1.0-rc1 比较。
