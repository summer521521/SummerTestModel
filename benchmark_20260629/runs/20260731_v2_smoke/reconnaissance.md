# V2 侦察记录

- 旧版与 20260730_incremental 保持只读。
- 当前清单、/api/tags、/api/show、/api/version 的原始响应保存于 `raw/api/`，并已对私有路径做脱敏。
- runner 使用流式 `/api/generate`，结果 JSONL 逐题 fsync；代码在父进程外的 `python -I -S` 子进程中执行。
- 本机未修改长期电源设置。
