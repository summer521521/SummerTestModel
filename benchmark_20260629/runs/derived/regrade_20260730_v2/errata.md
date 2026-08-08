# 20260730 增量结果 V2 派生审计

本目录只读取并重新解释昨晚结果，未修改 `20260730_incremental`。

- 旧 runner 使用 `num_predict=900`，对 thinking/reasoning 模型可能在最终答案前截断；本表按 `done_reason`、final response 与 thinking 分开标记。
- 旧代码 grader 使用宿主进程无约束 `exec`，且 AST 规则过严；本次仅记录新的安全策略分类，不执行旧回答。
- 旧安全赛道固定要求 SAFE/UNSAFE，和 Guardian/ShieldGemma 的 yes/no 语义不一致；V2 使用 adapter 记录原始输出并单独统计 invalid output。
- 旧 specialist 题量很少，不能代表完整视觉、OCR、工具或安全能力。
- 旧 planning grader 依赖固定参考时间；V2 规划评分改为结构化约束验证。
- `legacy_score` 保留原值，V2 派生状态和安全策略独立保存。
