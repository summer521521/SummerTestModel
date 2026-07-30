# 侦察记录

- 项目根：`SummerTestModel`。
- 历史正式 runner：`benchmark_20260629/scripts/benchmark.py`。
- 历史结果仅含模型名，不含 digest；本次将模型 digest 按原样持久化。
- 历史代码评分器会无约束 exec 模型回答；本次 runner 不调用该分支。
- 本次使用单线程 API 调用、每项 JSON 原始响应与 JSONL fsync。
