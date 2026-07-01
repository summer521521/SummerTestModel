# Benchmark 20260629

## 测试内容

本批次用于评测 Ollama 本地与云端模型在多用途场景下的基础能力：格式遵循、数学推理、长上下文检索、技术翻译、抗幻觉、代码修复和多约束规划。

## 模型范围

- `deepscaler:1.5b`
- `deepseek-r1:8b`
- `devstral-2:123b-cloud`
- `gemma4:e4b`
- `gpt-oss:120b-cloud`
- `granite4.1:8b`
- `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M`
- `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL`
- `huggingface.co/llmware/phi-4-mini-gguf:latest`
- `huggingface.co/lmstudio-community/DeepSeek-R1-0528-Qwen3-8B-GGUF:latest`
- `kaelri/hy-mt2:7b-q4_K_M`
- `lfm2.5:8b`
- `llama3.2:3b`
- `minimax-m3:cloud`
- `mistral:7b`
- `ornith:9b`
- `phi4-mini-reasoning:latest`
- `phi4-mini:latest`
- `qwen3-coder-next:cloud`
- `qwen3-coder:480b-cloud`
- `qwen3-vl:8b`
- `qwen3.5:4b`
- `qwen3.5:9b`
- `smollm2:1.7b`
- `starcoder2:7b`
- `translategemma:latest`

## 测试题

### format_json：JSON 格式与算术

- 类别：格式遵循
- 满分：10

```text
你是严谨的数据处理器。只输出一个 JSON 对象，不要 Markdown，不要解释。
订单金额：A=128.50，B=73.25，退款=-18.75。先求小计，再打 9 折。
输出字段：total（最终金额，保留 2 位小数的数字）、valid（布尔值）、code、summary。
code 必须是 OK- 加上最终金额乘以 100 后的整数。
```

### math_reasoning：多步数学推理

- 类别：推理
- 满分：10

```text
三台设备从 08:00 同时启动。A 每 6 分钟响一次，B 每 8 分钟响一次，C 每 15 分钟响一次。
问题：08:00 之后第一次三台再次同时响铃是什么时间？从 08:00 之后到这次同时响铃为止，如果每台设备每响一次都单独计数，总响铃次数是多少？
只输出 JSON：{"time":"HH:MM","count":数字}
```

### long_context：长上下文检索

- 类别：长上下文
- 满分：10

```text
下面是项目台账。请找出唯一满足条件的项目：status 是 PAUSED，owner 是 Lin，region 不是 APAC。只输出项目名和一句理由。
1. Atlas | owner=Chen | region=APAC | status=ACTIVE
2. Boreal | owner=Lin | region=APAC | status=PAUSED
3. Cinder | owner=Mei | region=EU | status=PAUSED
4. Delta | owner=Lin | region=NA | status=ACTIVE
5. Ember | owner=Rao | region=EU | status=ACTIVE
6. Fjord | owner=Lin | region=APAC | status=ACTIVE
7. Helios | owner=Lin | region=EU | status=PAUSED
8. Ion | owner=Qiu | region=NA | status=PAUSED
9. Juno | owner=Lin | region=LATAM | status=DONE
10. Kestrel | owner=An | region=EU | status=PAUSED
11. Luna | owner=Lin | region=APAC | status=PAUSED
12. Meridian | owner=Sun | region=NA | status=ACTIVE
13. Nova | owner=Lin | region=EU | status=ACTIVE
14. Orion | owner=Lin | region=NA | status=PAUSED_BUT_ARCHIVED
15. Pulse | owner=Zed | region=EU | status=PAUSED
16. Quartz | owner=Lin | region=APAC | status=DONE
```

### translation_terms：技术翻译与术语保留

- 类别：翻译
- 满分：10

```text
把下面中文翻译成自然、准确的英文。必须原样保留术语 RAG、KV cache、LoRA、p95 latency、tenant_id，不要添加原文没有的信息。
原文：为了降低 p95 latency，我们把 RAG 检索结果缓存 10 分钟，但不能跨 tenant_id 复用。微调只允许使用 LoRA，线上推理必须监控 KV cache 命中率。
```

### anti_hallucination：抗幻觉与信息边界

- 类别：可靠性
- 满分：10

```text
已知事实只有一句：黑曜计划在 2024 年启动。请回答：黑曜计划的负责人是谁、预算是多少、总部在哪？要求：不能编造；如果信息不足，请明确指出哪些无法确定。
```

### code_bugfix：代码修复

- 类别：代码
- 满分：10

```text
修复下面 Python 函数。要求：统计单词频次，忽略大小写，去掉英文标点；返回前 k 个(word, count)，按 count 降序、count 相同按 word 升序。只输出完整 Python 代码。

def top_k_words(text, k):
    counts = {}
    for word in text.split(' '):
        counts[word] = counts.get(word, 0) + 1
    return sorted(counts.items())[:k]

```

### planning_schedule：多约束日程规划

- 类别：规划
- 满分：10

```text
你是排班助手。为同一个人安排周六一天，必须满足：A 跑步 60 分钟，必须 07:00-10:00 之间开始，结束后连续 30 分钟洗澡恢复，恢复时不能做别的事；B 买菜 40 分钟，必须在超市 09:30-18:00 内完整完成；C 写作业 120 分钟，必须拆成两个连续 60 分钟块，中间不能插入别的任务，只能在家；D 和朋友吃饭固定 12:30 开始，90 分钟，餐馆；E 图书馆借书 30 分钟，必须 14:00-17:00 内开始；F 整理房间 45 分钟，只能在家，20:00 前完成。通勤：家-操场15，家-超市20，家-餐馆25，家-图书馆30，超市-餐馆15，超市-图书馆20，餐馆-图书馆10，操场-超市25，操场-餐馆35，操场-图书馆40。从家出发，最后回家。12:00-13:00 不能在路上。C 必须在 D 前完成，B 必须在 F 前完成，A 和 F 不能相邻。按三部分输出：结论、日程表、说明。
```
