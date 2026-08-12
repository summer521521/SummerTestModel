# SummerTestModel Benchmark 1.0-rc1 模型报告

[简体中文] · [English](model_report.md) · [阶段最终报告](docs/final_report.zh-CN.md) · [双语交互网站](https://summertestmodel-benchmark.walker-ethan.chatgpt.site)

## 范围

本报告只描述当前规范化基线：39/39 个本地模型、1,938 条任务记录与对应的 1,938 份本地不可变 raw；benchmark 为 `1.0-rc1`，发布评分器为 `1.0-rc1.1`。没有缺失 raw、重复 inference key、未解决评分错误或基础设施未完成记录。

结果反映记录的 Windows/Ollama 本机环境中的实际可用性，不是全球模型总榜，也不能与旧实验或厂商排行榜分数直接相加比较。

## 各赛道本地结果

| 赛道 | 本轮领先模型 | RC1 赛道均值 | 说明 |
| --- | --- | ---: | --- |
| Core | Qwen3-8B Q4 | 0.778 | 24 条评分记录 |
| Reasoning | Qwen3-8B Q4、Falcon-H1R-7B、LFM2.5 8B | 0.500 | 并列 |
| Code | Qwen3-VL 8B | 0.863 | 8 条评分记录 |
| Translation | Gemma4 E4B、Qwen3-8B Q4 | 1.000 | 并列 |
| Tools | Qwen3-8B Q4、LFM2.5 8B、Qwen3-VL 8B | 0.750 | 并列 |
| Long Context | Gemma4 E4B、Qwen3.5 9B | 0.500 | 并列 |
| Embedding | Qwen3 Embedding | 1.000 | 专用赛道 |
| Safety | Granite Guardian 4.1 8B | 1.000 | 专用赛道 |
| Medical | Nemotron 3 Nano 4B | 0.833 | 应用赛道 |
| OCR | DeepSeek OCR | 0.384 | 实验性 |
| Vision | Gemma4 E4B、Granite Vision、Ministral 3 8B | 0.125 | 实验性，并列 |

完整逐模型逐赛道数据见 [`public_results/rc1_track_scores.csv`](public_results/rc1_track_scores.csv)。性能遥测单独报告，不增加能力分。

## 运行与评分结果

- 7 次 absolute timeout；
- 104 条 truncation-related 记录；
- 19 条 runtime anomaly；
- 离线重评后未解决评分错误为 0；
- 已完成本地任务中的基础设施失败为 0。

三个 `CORE_PRACT_04` 评分器崩溃已在 `1.0-rc1.1` 中修复，直接使用已有 raw 离线重评，没有重新调用模型。详细分类见[失败分析](docs/rc1_failure_analysis.md)。

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
