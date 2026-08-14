# SummerTestModel

[简体中文] · [English](README.md)

SummerTestModel 用一台普通 Windows 游戏本，评测有趣且能力较强的 Ollama 小模型。项目现在以一个统一、可增量扩展的基线开始：**SummerTestModel Benchmark 1.0-rc1**。

> **建议从阶段最终报告开始阅读：**[设计依据、完整结果、39 个模型逐一分析、用途推荐与局限](docs/final_report.zh-CN.md)。网站版使用同一份结构化公开数据生成。

**双语交互网站：**[summertestmodel-benchmark.walker-ethan.chatgpt.site](https://summertestmodel-benchmark.walker-ethan.chatgpt.site)

## 当前实用快照

这是项目默认公开视图。原始严格 RC1 基线保持不可变；实用快照对全部已有 raw 离线重评，并只从一次明确标注的 50 条定向恢复中选择可评分且更好的结果。以后新增模型继续增量评测，不必重跑原来的 39 个模型。

| 项目 | 当前结果 |
| --- | --- |
| 本地模型 | 39/39 完成 |
| 本地任务记录 | 1,938 |
| 私有 raw 证据 | 1,938 份；无缺失 |
| 重复 inference key | 0 |
| 未解决评分错误 | 0 |
| 基础设施未完成记录 | 0 |
| Benchmark 版本 | `1.0-rc1` |
| 发布评分器 | `1.0-rc1.1` |
| 实用评分器 | `practical-regrade-1` |
| 定向恢复 | 50 条尝试；39 条选用；6 条能力任务仍无可评分 final |
| Ollama 运行快照 | 严格基线 `0.32.6`；定向恢复 `0.32.9` |

这次结果描述的是本机实际可用性，不是严格控制所有变量的实验室测试。Ollama 与运行环境版本随每次快照记录，不再作为永久兼容门槛。

## 结果怎么读

项目不计算万能总分。Core、Reasoning、Code、Translation、Tools、Vision、OCR、Long Context、Embedding、Safety、Medical 与 Performance 必须在各自赛道内解释；专用模型不会因不适用赛道被扣分。

以下实用赛道领先者按完成率共同解释；完整表同时保留严格分、实用分、coverage、完成率与恢复条数：

| 赛道 | 本轮领先模型 | 赛道均值 |
| --- | --- | ---: |
| Core | 6 个模型并列，包括 Qwen3-8B Q4、Qwen3-VL、Gemma4、Qwen3.5 9B | 0.879 |
| Reasoning | 13 个模型并列，当前夹具不足以区分头部 | 0.800 |
| Code | `olmo-3:7b-think` | 0.900 |
| Translation | `gemma4:e4b`、Qwen3-8B Q4、`qwen3-vl:8b` | 1.000 |
| Tools | Qwen3-8B Q4、`lfm2.5:8b`、`minicpm-v4.6`、`qwen3-vl:8b` | 0.909 |
| Vision | `qwen3-vl:8b` | 1.000 |
| OCR | `deepseek-ocr:latest` | 0.792，完成率 100% |
| Embedding | `qwen3-embedding:latest` | 1.000 |
| Safety | `granite4.1-guardian:8b` | 1.000 |
| Medical | Nemotron 4B、Qwen3.5 4B、Qwen3.5 9B | 0.800 |

Vision 与 OCR 的夹具仍少，而且语义分可能与完成率明显分离，因此仍属于实验性结果。Retention 仍是 `UNASSESSED`；用途推荐不等于保留或删除决定。

阅读入口：

- [阶段最终报告](docs/final_report.zh-CN.md) · [English](docs/final_report.en.md)
- [双语交互网站](https://summertestmodel-benchmark.walker-ethan.chatgpt.site)
- [RC1 完整结果说明](docs/rc1_results.md)
- [当前模型报告](model_report.zh-CN.md)
- [39 模型结构化评估](public_results/rc1_model_assessments.json)
- [实用逐模型逐赛道数据](public_results/rc1_practical_track_scores.csv)
- [定向恢复对照](public_results/rc1_practical_recovery_20260813.csv)
- [严格基线逐赛道数据](public_results/rc1_track_scores.csv)
- [性能遥测](public_results/rc1_performance.csv)
- [失败分析](docs/rc1_failure_analysis.md)
- [脱敏本地结果记录](public_results/rc1_baseline_20260809.jsonl)
- [独立云端参考结果](public_results/rc1_cloud_comparison_20260812.jsonl)

云端参考不进入 39 模型本地基线。两个云端模型完成 142 条任务；三个已退役服务条目返回 HTTP 410，只记录为可用性失败，不计模型能力 0 分。

## 测试机器

| 部件 | 记录环境 |
| --- | --- |
| 系统 | Windows 11 家庭中文版，build 26200 |
| CPU | Intel Core i5-13500HX，14 核 / 20 线程 |
| 内存 | 31.8 GiB |
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU，8 GiB VRAM |
| Python | 3.12.10 |
| Ollama | 严格基线为 0.32.6；定向恢复为 0.32.9 |

详见[机器配置](docs/machine_profile.md)与[运行时版本政策](docs/ollama_runtime_policy.md)。

## 以后新增一个模型

新增模型不需要重跑 39 模型基线。增量流程会记录实际 digest，要求显式选择已有的可比能力分配，只执行适用的冻结赛道，每题 checkpoint，并导出新的脱敏结果。

```powershell
python scripts/incremental_model.py inspect --model "new-model:tag"
python scripts/incremental_model.py prepare --model "new-model:tag" --reference-model "existing-model:tag"
python scripts/incremental_model.py run --model "new-model:tag" --reference-model "existing-model:tag" --allow-inference
```

详见[增量模型流程](docs/INCREMENTAL_MODELS.md)。执行器不会根据模型名字猜 capability，也不会自行设计题目或评分规则。

## 仓库结构

```text
config/                    # 冻结的 RC1 manifest、profile 与执行政策
inventory/                 # 已安装模型元数据与官方来源映射
public_results/            # 当前脱敏 RC1 结果快照
scripts/                   # runner、scorer、validator 与增量工作流
tests/                     # 执行器与评分器回归测试
docs/                      # 当前报告和操作文档
site/                      # 双语结果网站源码
private_benchmark/         # 私有 benchmark 内容；Git ignored
private_runs/              # 本地不可变 raw；Git ignored
benchmark_20260629/        # RC1 之前的历史实验
legacy_evidence/           # 其他历史证据
```

## 历史参考

旧 V1、V2 与增量实验保留在 [`benchmark_20260629/`](benchmark_20260629/) 和 [`legacy_evidence/`](legacy_evidence/) 中，只用于历史审计，不属于当前结果和排名体系。见[简要历史索引](docs/legacy_history.md)。

## 双语维护规则

项目首页、阶段最终报告与当前模型报告同时维护中英文版本。机器可读 manifest、schema、字段名和代码保持英文，确保只有一套可执行接口；双语说明链接到同一份底层数据，不复制两套结果。
