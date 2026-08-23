# 01 · Mindset — Model + Harness 范式

> 本文件讲"为什么这么设计"而不是"怎么写代码"。读完 5 分钟,理解 Agent 工程的根本立场。

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
3. **工具不抛异常,错误编码成消息**——`isError:true` 让模型自决
4. **权限三态(allow/ask/deny),deny 永不弹窗**——安全边界是代码,不是 UI
5. **信任模型但不信模型的输出**——校验在边界,信任在内部
6. **证据流是 append-only,状态是派生**——JSONL + replay,不是数据库里塞状态

---

引用与致谢:本范式提炼自 `shareAI-lab/learn-claude-code` (commit f9e8b280) README §"Where Agency Comes From"、§"The Mindshift"、§"Core Pattern";`meisijiya/learn-workbuddy` README §"Harness 总图"、§"三大根本矛盾"、§"Agent 角色分工";`dg-ai-notes.pages.dev` M02 三层架构、M03 Agent Loop、M07 事件驱动。