# 06 · Loop Engineering — 让 Agent 自己跑起来

> 本文件讲"如何把单次对话升级为持续运行的 Agent"。读完 5 分钟,理解 Loop 工程的 4 种循环形态、6 个原语、4 silent costs。

## 一句话 / 核心概念

**Loop Engineering = 从手动驾驶到自动化循环**(Addy Osmani / walkinglabs L13)。不是写一个新的 if-else 调度器,而是在同一个 `while True` 内核上,塞入触发源(goal / timer / maker-checker / event)、恢复机制、外部状态,让一个会话从"用户问一次答一次"变成"持续响应事件、定时跑任务、长时守护进程"。

Loop 不是 sub-agent 的别名。一个 Loop 还是一个 LLM + 一个 `messages[]`,只是触发它下一轮的源从"用户说话"扩展到"时间到了 / 外部事件来了 / 上轮结果还没好"。

## 4 种循环

不同的"驱动下一轮的方式"决定了 Loop 的形态:

| 循环 | 触发源 | 典型场景 | 关键参数 |
|---|---|---|---|
| **Goal-driven** | 用户给一个 goal,跑直到 goal_gate 通过 | "实现这个功能"、"修这个 bug" | `goal_gate` 评估器、`maxContinuations` 防死循环 |
| **Timer-driven** | cron / setInterval 触发 | "每小时巡检一次日志"、"每天跑测试" | cron 表达式、时区、并发锁(防重叠) |
| **Maker-Checker** | 一个 loop 产出,另一个 loop 评 | "写代码 + 评审"、"生成 + 事实核查" | evaluator 模型(便宜即可)、独立信号源(Linter / test runner) |
| **Event-driven** | webhook / 文件 watcher / 消息队列触发 | "PR opened 自动评审"、"文件改动自动 lint" | 事件去重、幂等性、背压控制 |

> **共性**:每种 Loop 都共享同一个 30 行 `while True` 内核。差异只在"什么算下一轮的触发"和"什么算该停下"。

## 6 原语

walkinglabs L13 把 Loop 工程切成 6 个最小原语。每个 Loop 几乎都需要全部 6 个,只是组合方式不同:

| # | 原语 | 作用 | 典型实现 |
|---|---|---|---|
| 1 | **Automations** | 触发源(timer / webhook / goal) | cron 配置 / webhook endpoint / file watcher |
| 2 | **Worktrees** | 每个 Loop 实例有独立工作区 | git worktree per session / 临时目录 + cleanup |
| 3 | **Skills** | 任务相关知识按需加载 | `SKILL.md` 目录 + `load_skill` 懒加载 |
| 4 | **Connectors** | 外部系统(数据库 / API / SaaS) | MCP servers / 自定义 client |
| 5 | **Sub-agents** | 复杂任务拆解 | 独立 `messages[]` + 只回最终文本 + 隔离上下文 |
| 6 | **External State** | 跨重启的事实持久化 | JSONL append-only transcript + 任务图文件 + head anchor |

> **判断**:6 原语缺一不可——少了 Automations,你没有触发;少了 Worktrees,Loop 实例互相覆盖;少了 Skills,模型瞎猜;少了 Connectors,Loop 是孤岛;少了 Sub-agents,任务复杂度爆;少了 External State,重启即丢。

## 4 Silent Costs

Loop 工程跑久了会**悄悄欠下 4 种债**,不像 bug 那么明显,但累积到一定规模 Loop 就跑不动了:

| 债 | 表现 | 检测 | 预防 |
|---|---|---|---|
| **Verification Debt** | 模型说"做完了"但实际错了;无人复查 | transcript 里 goal_gate 通过率 < 70% | 强制独立 evaluator + 测试必须跑通才能 settled |
| **Comprehension Rot** | 长期 Loop 里 Skills / Memory 膨胀,模型渐渐分不清主次 | prompt token 用量逐周上涨 | 定期审计 Skills / Memory,过期的删 |
| **Cognitive Surrender** | 团队放弃 review,所有事情都甩给 Loop 跑 | Loop 产出的 PR review 率 < 30% | 强制 human-in-the-loop,高风险操作必须 ASK |
| **Token Blowout** | 单次 Loop 烧光 token budget | 单次 Loop avg cost 异常 | 硬上限 + 每 1000 步检查 + 自动 abort |

> **治疗**:4 种债都不会自己消失,都需要 Harness 层主动治理。`scripts/verify.py` 这类"周期性重置 + 审计"的工具不是 nice-to-have,是 Loop 工程的免疫系统。

## Generator / Evaluator Separation

**写代码 ≠ 验收代码**。同一个模型既生成又评审自己产出,质量门形同虚设:

| 角色 | 责任 | 典型选择 |
|---|---|---|
| **Generator** | 产出代码 / 答案 / 计划 | 最强的模型(Opus / Sonnet / 旗舰) |
| **Evaluator** | 评审产出是否达标 | 更便宜的模型(Haiku / 规则 / Linter / test runner) |

> **最小验证**:Generator 写完代码,Evaluator 跑一遍测试套件 + 静态检查 + 至少一条 critic prompt("这段代码哪里错了?")。如果 Evaluator 也用同款旗舰模型 + 同样的 prompt,等于没验证。

## 何时用 / 何时不用

**何时用 Loop Engineering**:

| 信号 | 说明 |
|---|---|
| 任务需要**持续运行**(小时 / 天级) | cron / daemon / 长会话守护 |
| 触发源**不是用户**(事件 / 时间 / 状态变化) | webhook / 定时 / 文件改动 |
| 同一类任务**重复多次**且模式可沉淀 | 自动化巡检 / 批量重构 / 流水线 |
| **人在回路**而非人在驾驶 | 决策仍由人做,Loop 只做执行与监控 |

**何时不用**:

| 信号 | 说明 |
|---|---|
| 任务**一次性**且需用户全程对话 | 用普通 `while True` 即可,不要套 Loop 框架 |
| 决策**强不确定**且需要人类判断 | Loop 不替代决策,只替代重复执行 |
| **没有 External State** | 重启即丢的 Loop 不可信;要么补 External State,要么不要跑 |
| **没有验证机制** | 没有 goal_gate / test runner / evaluator 的 Loop 是定时炸弹 |

## 引用与致谢

本文件提炼自 `walkinglabs/learn-harness-engineering` L13 §The Six Primitives of a Loop + §Four Silent Costs + §Generator/Evaluator Separation;`WanLanglin/-awesome-cc-harness` §3.2 The Seven Continue Sites(与本文件互补——Continue Site 是"Loop 中断如何续",Silent Cost 是"Loop 长期会欠什么")。所有内容均为重新表述,不复制上游逐字原文。

## 附录 · Loop 工程的 5 个常见误解

**误解 1:Loop 就是 cron 跑 Agent**

- 错。Loop 不是"每隔 N 分钟问模型一次",而是"事件触发 + 持续状态 + 自动续跑"。纯 cron 缺乏 Continue Sites 的恢复机制,跑几次后必然卡死。

**误解 2:Loop 越多越好**

- 错。Loop 数与可观测性成反比。3 个 Loop + 清晰黑板比 30 个 Loop + 隐式共享 state 更可控。

**误解 3:Loop 工程的瓶颈是模型**

- 错。瓶颈通常是 External State 的写入路径——append-only JSONL + head anchor 在并发 Loop 下成为热点。L1 → L3 升级时这个瓶颈最先出现。

**误解 4:Loop 一旦跑通就不需要改**

- 错。Loop 是"模型 + Harness"的反复摩擦面——模型升级、provider 切换、新工具接入都会让 Loop 出问题。每周至少看一次 transcript。

**误解 5:Loop 工程没有 ROI**

- 错。Loop 工程的 ROI 在"重复任务被自动化 + 人不在场也能产出"。计算方式:每周节省的人时 × 时薪 - Loop 维护成本 = 周净收益。如果收益 < 0,撤掉 Loop,别硬撑。