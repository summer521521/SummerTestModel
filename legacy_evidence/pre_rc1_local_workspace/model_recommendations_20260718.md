# Ollama 模型替换与新增建议

更新时间：2026-07-18

## 筛选前提

- 已核对硬件：NVIDIA GeForce RTX 4060 Laptop GPU，8GB 显存；系统内存约 32GB。
- 本地部署上限按约 9B 参数处理。模型文件大于显存时可能发生 CPU/RAM offload，能运行不等于速度理想。
- 当前通用测试共 26 个模型、7 项测试、满分 70。分数只代表本项目测试，不代表模型全部能力。
- 所有命令均为 Ollama 本地命令；先 `pull`、再测试，确认替代成功后再 `rm`。

## 一、优先替换

| 当前模型 | 实测 | 建议替换为 | 理由 | 依赖体量/定位 | 本行命令 |
| --- | ---: | --- | --- | --- | --- |
| `starcoder2:7b` | 10/70 | `qwen2.5-coder:7b` | 当前代码测试 0/10，整体旧且格式、推理、规划均弱；Qwen2.5-Coder 是专门的代码生成、代码推理和修复模型。 | 约 4.7GB，32K 上下文；代码专用 | `ollama pull qwen2.5-coder:7b`<br>`ollama run qwen2.5-coder:7b`<br>验证后：`ollama rm starcoder2:7b` |
| `qwen3.5:4b` | 7/70 | `gemma3:4b` | 当前是全表最低分之一；Gemma 3 4B 支持文本和图像，128K 上下文，能覆盖轻量问答、总结、图像理解，比保留一个低分通用模型更有价值。 | 官方 Ollama 体量约 3.3GB；多模态通用 | `ollama pull gemma3:4b`<br>`ollama run gemma3:4b`<br>验证后：`ollama rm qwen3.5:4b` |
| `qwen3.5:9b` | 17/70 | `ministral-3:8b` | 当前模型虽然代码测试 10/10，但 JSON、数学、检索、翻译和规划很差；Ministral 3 8B 面向边缘部署，支持图像、多语言、工具调用、JSON 和 256K 上下文，更适合作为新的通用本地候选。 | 约 6.0GB；多模态、Agent、长上下文 | `ollama pull ministral-3:8b`<br>`ollama run ministral-3:8b`<br>验证后：`ollama rm qwen3.5:9b` |
| `deepseek-r1:8b` | 21/70 | `nemotron-3-nano:4b` | 当前 R1 8B 在本测试中速度慢、格式和规划失败；Nemotron 3 Nano 4B 是专门面向 Agent 的开放模型，支持思考/非思考两种模式，适合作为有趣的推理和工具调用对照组。 | 4B 本地版；英文、德文、西文、法文、意大利文、日文为官方列出的支持语言，中文不是它的强项 | `ollama pull nemotron-3-nano:4b`<br>`ollama run nemotron-3-nano:4b`<br>确认中文表现后：`ollama rm deepseek-r1:8b` |

## 二、建议新增，但不立即删除旧模型

| 新模型 | 用途 | 为什么值得试 | 本行命令 |
| --- | --- | --- | --- |
| `gemma3n:e4b` | 低资源多模态、日常助手 | 使用 selective parameter activation，官方定位就是笔记本、平板和手机；有效规模约 4B，适合和 `gemma4:e4b` 对比速度、图像理解和内存占用。 | `ollama pull gemma3n:e4b`<br>`ollama run gemma3n:e4b` |
| `granite4:7b-a1b-h` | 工具调用、结构化输出、RAG | IBM Granite 4 的混合架构实验款，官方强调指令遵循、工具调用、RAG、代码和 FIM；总规模 7B、激活规模 1B，适合测试低激活量模型。 | `ollama pull granite4:7b-a1b-h`<br>`ollama run granite4:7b-a1b-h` |
| `functiongemma:270m` | Function calling 路由器 | 不是聊天模型，而是专门做函数调用的 270M 小模型；可作为 Agent 前置分类器或工具选择器，速度和占用都很低。 | `ollama pull functiongemma:270m`<br>`ollama run functiongemma:270m` |
| `shieldgemma:2b` | 安全审查/内容过滤 | 专门输出安全判定，不应该拿来替换聊天模型；可给本地 Agent 增加输入、输出安全检查。 | `ollama pull shieldgemma:2b`<br>`ollama run shieldgemma:2b` |
| `medgemma1.5:4b` | 医疗文本与医学图像 | 只有在你确实需要医疗资料、检验单或医学图像分析时才值得部署；它是医疗专用视觉模型，不适合作为通用助手。 | `ollama pull medgemma1.5:4b`<br>`ollama run medgemma1.5:4b` |

## 三、建议保留

| 当前模型 | 实测/用途 | 保留理由 |
| --- | --- | --- |
| `ornith:9b` | 52/70，本地第一名 | 当前最强本地通用基线，代码、检索、可靠性表现尤其好。 |
| `granite4.1:8b` | 45/70 | 本地综合第二梯队，代码、长上下文、可靠性和翻译都稳定。 |
| `lfm2.5:8b` | 41/70 | 代码、可靠性和速度表现不错，适合轻量本地任务。 |
| `gemma4:e4b` | 40/70 | JSON、长上下文、可靠性和翻译表现好；虽然模型文件较大，但有多模态和新架构价值。 |
| `hf.co/lmstudio-community/Qwen3-8B-GGUF:Q4_K_M` | 39/70 | 新增模型中最高；JSON、检索、可靠性和翻译不错，仍值得继续针对代码/规划测试。 |
| `hf.co/unsloth/SmolLM3-3B-GGUF:UD-Q4_K_XL` | 36/70 | 体量小、速度快，可靠性和长上下文不错，可保留作轻量快速模型。 |
| `translategemma:latest` | 翻译专用 | 通用测试只有 21/70，但它不是通用模型；如果常做翻译，不应按总分删除。 |
| `qwen3-vl:8b` | 视觉专用 | 通用文字测试只有 14/70，不能代表图像能力；除非你已有更好的视觉模型并完成图像对测，否则保留。 |
| `qwen3-embedding:latest` | Embedding | 不是对话模型，不能参与普通文字排名；用于向量检索，应该单独保留。 |

## 四、可清理但不急于删除

完成替代模型测试后，可考虑清理以下旧基线：

```powershell
ollama rm starcoder2:7b
ollama rm qwen3.5:4b
ollama rm qwen3.5:9b
ollama rm deepseek-r1:8b
```

如果硬盘空间紧张，再考虑：

```powershell
ollama rm llama3.2:3b
ollama rm phi4-mini:latest
ollama rm phi4-mini-reasoning:latest
ollama rm smollm2:1.7b
```

这里不建议直接删除 `mistral:7b`，因为它是一个清晰的老基线；等 `ministral-3:8b` 完成对测后再决定。云端模型显示 `-`，不占用本地模型文件的主要空间，也不属于本地替换对象。

## 五、推荐执行顺序

第一批优先下载，避免一次占满显存：

```powershell
ollama pull qwen2.5-coder:7b
ollama pull gemma3:4b
ollama pull ministral-3:8b
ollama pull nemotron-3-nano:4b
```

单模型快速检查：

```powershell
ollama run qwen2.5-coder:7b
ollama run gemma3:4b
ollama run ministral-3:8b
ollama run nemotron-3-nano:4b
```

确认模型可调用后，再在项目基准中测试。不要先删除旧模型，因为需要保留旧结果作为回归对照。测试完成并确认替代关系后，再执行清理命令。

## 六、结论

最值得立即尝试的组合是：

1. `qwen2.5-coder:7b`：替换 `starcoder2:7b`，补足本地代码专长。
2. `gemma3:4b`：替换 `qwen3.5:4b`，补足轻量多模态和长上下文。
3. `ministral-3:8b`：替换 `qwen3.5:9b`，作为新的多模态 Agent 候选。
4. `nemotron-3-nano:4b`：替换 `deepseek-r1:8b`，观察小型思考模型和混合架构的实际收益。
5. `gemma3n:e4b`、`granite4:7b-a1b-h`、`functiongemma:270m`：作为有趣的专项增量，不建议直接当通用模型替换。

## 官方资料

- [Gemma 3 - Ollama](https://ollama.com/library/gemma3)
- [Gemma 3n - Ollama](https://ollama.com/library/gemma3n)
- [Ministral 3 - Ollama](https://ollama.com/library/ministral-3)
- [Qwen2.5-Coder - Ollama](https://ollama.com/library/qwen2.5-coder)
- [Granite 4 - Ollama](https://ollama.com/library/granite4)
- [Nemotron 3 Nano - Ollama](https://ollama.com/library/nemotron-3-nano)
- [FunctionGemma - Ollama](https://ollama.com/library/functiongemma)
- [ShieldGemma - Ollama](https://ollama.com/library/shieldgemma)
- [MedGemma 1.5 - Ollama](https://ollama.com/library/medgemma1.5)
