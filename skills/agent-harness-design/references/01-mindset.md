# 01 · Mindset — Model + Harness 范式

> 本文件讲"为什么这么设计"而不是"怎么写代码"。读完 5 分钟,理解 Agent 工程的根本立场。

## 视角选型

Agent 工程的"视角"在不同上游里被切成不同形状。本 skill 用统一对照表把两个上游的视角合起来,做设计时先选视角再选 reference。

### 5 子系统(walkinglabs L02)

| # | 子系统 | 一句话 |
|---|---|---|
| 1 | **Prompt** | system message 的组装(token 预算、Skills catalog、Memory 召回) |
| 2 | **Context** | 输入语料管理(持久化、剪裁、替换、摘要四步管道) |
| 3 | **Loop** | 单进程循环控制(`while True` 内核 + 6 叠加层) |
| 4 | **Tools** | 行动表面(schema/handler/policy 三合一 + 并发调度) |
| 5 | **Orchestration** | 多 Agent 图(节点、边、共享状态、路由规则) |

### 3 支柱(WanLanglin §1.2)

| # | 支柱 | 核心问题 |
|---|---|---|
| 1 | **Context(上下文)** | 模型能"看到什么"——决定推理质量 |
| 2 | **Tools(工具)** | 模型能"做什么"——决定行动力 |
| 3 | **Loop(循环)** | 模型能"持续多久"——决定任务粒度 |

> **两套视角的对应**:walkinglabs 的 5 子系统 ≈ WanLanglin 3 支柱 + Orchestration + Prompt 工程化层。`Prompt` 在 WanLanglin 视角里被吸收进 `Context`;`Orchestration` 在 WanLanglin 视角里被吸收进 `Tools`(tools-as-protocol)。

### 何时看哪个 reference

| 你卡在哪里 | 先看哪个 reference |
|---|---|
| 不知道从哪里开始 / 想统一心智 | [`01-mindset.md`](01-mindset.md)(本文件) |
| 14 个机制哪些必须 / 怎么验 | [`02-checklist.md`](02-checklist.md) |
| 已经做完,担心某个坑没踩 | [`03-antipatterns.md`](03-antipatterns.md) |
| 想让 Agent 自己跑(cron/webhook/事件) | [`06-loop-engineering.md`](06-loop-engineering.md) |
| 想把单 Agent 拆成多 Agent 团队 | [`07-graph-engineering.md`](07-graph-engineering.md) |
| 想参考 Pi/Claude Code/Codex/DeepSeek 的取舍 | [`08-frontier-designs.md`](08-frontier-designs.md) |
| 想做交叉校准 / 引用源标注 | [`05-source-synthesis.md`](05-source-synthesis.md) |

## 一、Agent = Model + Harness

**Agency 来自模型训练,不是来自外部代码编排**。一个能工作的 Agent 产品 = Model(LLM)+ Harness(让模型工作的世界)。

| 历史里程碑 | 训练的模型 | Harness(环境) |
|---|---|---|
| 2013 DQN Atari | 一个 CNN | 模拟器 + 像素/分数 |
| 2019 OpenAI Five Dota 2 | 五个神经网络(自我对弈) | Dota 2 客户端 |
| 2019 AlphaStar | 一个神经网络 | StarCraft II 引擎 |
| 2024-2025 LLM 编程 Agent | Claude/GPT/Gemini | IDE + 终端 + 文件系统 |

每一条都遵循同一模式——**模型是决策者,Harness 是行动空间**。模型决定何时调工具,代码执行模型要的。

## 二、Harness 的五元定义(功能视角)

```
Harness = Tools + Knowledge + Observation + Action Interfaces + Permissions

    Tools:          文件 I/O、Shell、网络、数据库、浏览器
    Knowledge:      产品文档、领域资料、API 规范、风格指南
    Observation:    git diff、错误日志、浏览器状态、传感器数据
    Action:         CLI 命令、API 调用、UI 交互
    Permissions:    沙箱隔离、审批流程、信任边界
```

但从工程视角,Harness 由 14 个核心机制组成——见 `02-checklist.md`。五元定义是"做什么",14 机制是"怎么做"。

### 优化 ROI:模型 vs Harness

模型训练昂贵,但 Harness 调优的 ROI 显著高于模型优化:

| 优化方向 | 典型收益 | 成本量级 |
|---|---|---|
| **模型优化**(换基座 / SFT / RLHF) | +3–5% 任务成功率 | 月级工程量 + 大量 GPU + 重新评估管线 |
| **Harness 优化**(改上下文管道 / 加权限 / 加 Loop 叠加) | **+14%** 端到端成功率 | 几天到几周;改几十行 dispatch / hooks |

**Opus 4.5 案例**(WanLanglin §1.5 引用):在 SWE-Bench Verified 子集上,Anthropic 用 Opus 4.5 + Claude Code 风格的 Harness(含显式 planning + tool dispatch + audit log)做 harness-side ablation——纯模型层只换 Opus 4.5 baseline 的成功率为 ~62%;同样的 Opus 4.5 + 完整 Harness 达到 ~76%(+14 pp);而换成更大或更新的基座不调 Harness 收益 < 3 pp。

> **数据来源:WanLanglin §1.5,单一来源,未交叉复现**——这两个数字来自 WanLanglin 逆向 Claude Code 512K LOC 后的复盘,本仓库尚未独立跑过 SWE-Bench 复现。引用时建议标注"WanLanglin 单一来源,未交叉复现"。

## 三、什么是 Agent,什么不是 Agent

### Agent 是

- 训练好的神经网络 + 让它能在某环境工作的基础设施
- 模型的 judgment + harness 的 execution

### Agent 不是

- "LLM API + if-else + 节点图 + 硬编码路由"——这是 **Rube Goldberg 机器**,披着 Agent 外衣的工作流脚本
- "Drag-and-drop AI Agent builder"——把 if-else 拖到画布上,不产生 Agency,只产生复杂度
- "Prompt-chain orchestration library"——把 LLM 调用串成瀑布,祈祷足够多胶水代码能"涌现"出自主行为

> **判定标准**:你做的要么是"训练模型",要么是"构建 Harness",只有这两件事。其他都是中间层。

## 四、三大根本张力(贯穿所有设计)

Agent 工程的全部复杂性,都来自这三对根本张力。理解它们,比记住任何机制都重要。

### 张力 1:Agency 来自模型 vs Harness 必须给边界

模型是大脑,但大脑不能裸奔——它必须住在边界清晰的世界里。

**信任边界内放手,边界外做约束**。Harness 不替模型做判断,只划可执行边界:

- 模型说"我要 rm -rf /" → 闸门 DENY,不执行
- 模型说"我想执行 npm test" → ALLOW,直接跑
- 模型说"我想 push 到 main" → ASK,问用户

但**不要替模型决定"该不该用 TodoWrite"**——那是模型的事;Harness 只做"连续 3 轮没用就提醒"。

### 张力 2:Loop 必须恒定 vs 机制持续扩张

`while True + tool_use + tool_result` 这个 30 行循环是**不可触碰的内核**。但上层要加的工具、权限、记忆、团队、MCP 是几十个。

**解法:三个注入点接入,绝不直接改循环体**:

| 注入点 | 例子 |
|---|---|
| `TOOL_HANDLERS` dispatch map | 加工具、加 Skills、接 MCP |
| `HOOKS` registry | PreToolUse / PostToolUse / UserPromptSubmit / Stop |
| System prompt 组装 | 注入 Skills catalog、Memory 召回结果、上下文预算 |

> **检验**:Loop 函数本身在加完所有机制后,行数有没有增加?没有 = 通过。有 = 重构。

### 张力 3:上下文无限增长 vs 上下文硬上限

每次 tool_use 都往 messages[] 追加。LLM 有 context window 硬上限。中间怎么取舍?

**解法:按"信息损失和成本"从低到高排,组成压缩管道**:

1. **持久化**(0 API 调用)——超大的 tool_result 写磁盘,留指针
2. **剪裁**(0 API 调用)——messages 超过 N,旧的整段写存档
3. **替换占位符**(0 API 调用)——旧的 tool_result 用占位符代替
4. **摘要**(1 API 调用)——实在放不下才生成结构化摘要

**三步零模型调用,最后一步才花钱**。可重读的(工具结果)优先压缩;摘要放最后。

### 3 级 Harness 成熟度阶梯

不是所有 Harness 工程都做到同一深度。WanLanglin §1.5 把 Harness 工程按"服务多少用户 / 多深治理"切成 3 级,每一级的核心动作不一样:

| 级别 | 形态 | 时间投入 | 核心动作 | 退出标准 |
|---|---|---|---|---|
| **L1 Individual** | 1 个开发者 + 1 个 LLM 终端 | 1–2 小时 | 把单进程 Loop 跑通;1 个 prompt + 5 个工具 + 内存中的 memory | Loop 能稳定完成一个真实任务 |
| **L2 Small team** | 3–10 个开发者 + 共享 harness repo | 1–2 天 | 加权限/Hooks、SubAgent、Task System、audit log、CI 上跑通 | 团队任何成员拉下来就能跑 |
| **L3 Organization** | 全公司 + 多产品线 + 治理委员会 | 1–2 周 | 加 Multi-Provider Adapter、Skills 目录、MCP 适配、policy-as-code、可观测性 + 计费 | 多个产品线共享同一 Harness,变更通过 review |

> **判断**:L1 是工程,L2 是工程 + 协作,L3 是工程 + 治理 + 商业。多数 Agent 项目死在 L1 → L2 的过渡——把个人脚本"团队化"时,Loop 边界、工具并发、权限政策需要重写一遍。预算上 L2 比 L1 贵 10×,L3 比 L2 贵 5×。

## 五、内核 + 叠加:Loop 的工程哲学

**Loop 内核只有 10 行**:

```
while True:
    response = call_model(messages, tools, system)
    messages.append(assistant_turn(response))
    if no tool_use in response: return
    results = execute_tools(response.tool_calls)
    messages.append(tool_results(results))
```

**叠加 = 产品功能**:

- `steering`——紧急插队,用户中途想打断
- `followUp`——任务追加,LLM 想继续就继续
- `prepareNextTurn`——动态切模型(便宜做粗筛,贵的做推理)
- `shouldStopAfterTurn`——安全阀,某些情况必须停
- `goal_gate`——独立评估器判断 goal 是否真满足

**叠加加在 Loop 外,不写进 Loop 里**。

## 六、两条事件管道:订阅 vs 决策

做事件监听时,先问自己:**Agent 等不等我?**

| 管道 | 用途 | 等不等 Agent | 典型用途 |
|---|---|---|---|
| **subscribe** | 只读观察 | 不等(返回丢弃) | 落库、审计、监控、UI 渲染 |
| **on(扩展钩子)** | 能动手 | 等(await 读返回值) | 权限拦截、参数改写、上下文注入 |

**判错会静默命中不了**:subscribe 里写 `tool_call` 处理,逻辑不会跑——subscribe 漏收那 5 个决策点。

## 七、核心哲学 6 句话

1. **模型是大脑,Harness 是操作系统**——别把两者混在一起改
2. **Loop 恒定,机制扩张**——加新功能永远通过 dispatch / hooks / prompt 注入
3. **stream/provider 层不抛异常(发 `{ type: "error" }` 事件,M04);tool 层的 `execute` 应该 throw,pi-agent 自动转 `isError:true` 结果交 LLM 自己纠正(P05)**——错误编码进 stream 事件与 tool 结果两条路径并存
4. **权限三态(allow/ask/deny),deny 永不弹窗**——安全边界是代码,不是 UI
5. **信任模型但不信模型的输出**——校验在边界,信任在内部
6. **证据流是 append-only,状态是派生**——JSONL + replay,不是数据库里塞状态

---

📦 **Federation**: For `pi-coding-agent` v0.83.0 API specifics (createAgentSession / defineTool / pi.on / session.subscribe / SSE streaming), install the upstream `dg-piagent` skill — see pointer in `docs/awesome-skills.md`. Our skill stays vendor-neutral; `dg-piagent` stays SDK-versioned.

引用与致谢:本范式提炼自 `shareAI-lab/learn-claude-code` (commit f9e8b280) README §"Where Agency Comes From"、§"The Mindshift"、§"Core Pattern";`meisijiya/learn-workbuddy` README §"Harness 总图"、§"三大根本矛盾"、§"Agent 角色分工";`dg-ai-notes.pages.dev` M02 三层架构、M03 Agent Loop、M07 事件驱动;`walkinglabs/learn-harness-engineering` L02 §Five-Subsystem;`WanLanglin/-awesome-cc-harness` §1.2 Three Pillars + §1.5 ROI 量化 + Implementation Tiers。