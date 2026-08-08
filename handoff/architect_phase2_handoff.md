# Architect Phase 2 Handoff — SummerTestModel Benchmark 1.0-rc1

日期：2026-08-08。此文件只记录本地工程事实和已明确实现的协议，不设计题目、评分器或模型排名。

## 本次实现

- `benchmark_version` 固定为 `1.0-rc1`；V1/V2 仅为 `Legacy Experimental Evidence`，旧分数未继承、旧 evidence 未删除。
- RC1 候选计划从现有 inventory 生成：44 个条目、39 个 local candidate、5 个 cloud excluded；39 个 local 全部 `RETAINED_CANDIDATE`，total params <=10B，retention 全部 `UNASSESSED`。
- 固定 12 个 track ID，无 overall/universal score。
- 固定 8K/32K verified context tiers；32K 仅在 declared context >=32768 时列入，未验证 128K/256K/1M。
- 固定 generation profiles、temperature 0、seed=42 的“仅支持时发送”策略，并禁止 `format=json` 与 JSON schema constrained decoding。
- 真实 adapter 支持 `/api/chat`、`/api/generate`、`/api/embed`，保留请求、stream chunks、thinking、final answer、tool calls、done reason、timing 和错误；thinking 与 final answer 分开。
- transport retry=1；connection refused 连续 3 次后 circuit open，每 30 秒 healthcheck，最多恢复 900 秒，不自动重启 Ollama。
- 一次只加载一个模型，提供 keep_alive=0 unload 接口；adapter 未被用于正式推理。
- 通用 mock tool loop 最多 3 rounds；没有创建正式 tool schema。
- code harness 继续执行 AST gate、`python -I -S`、隔离子进程、临时 cwd、超时和禁用危险 builtins/modules。

## Doctor 状态

当前必须是 `NOT_READY`。本次验证时本地 Ollama 服务也未运行（客户端 0.32.6 可用，`/api/version` 不可达）；执行器没有自动启动或重启服务。除此之外，以下内容仍由架构师提供：

1. frozen task manifest 及 SHA256；
2. frozen scorer manifest 及 SHA256；
3. final model execution plan hash binding；
4. final track/task assignments 与 hash binding。

在这些内容齐全并通过 hash 校验前，Luna Max 必须停止，不得开始模型生成。

## 验证证据

已通过：

- `python -m unittest tests.test_executor_core -v`：9 tests OK；
- Python compile：changed scripts/tests compile successfully；
- mock failure isolation、duplicate skip、corrupt-state recovery、tool-loop limit、adapter thinking separation 均有测试；
- `scripts/build_rc1_model_plan.py`：39 local / 5 cloud counts consistent。

未执行：正式 benchmark、正式题目、正式 scorer、模型生成、模型下载或删除、inventory 修改、retention 判断。

## 架构师需要决定

task 内容、ground truth、scorer 语义、权重、模型适用 track、最终 manifest hashes，以及是否接受当前 code harness 的隔离边界。以上决策不由 Codex Medium 或 Luna Max 代替。
