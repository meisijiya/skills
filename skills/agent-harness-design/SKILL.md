---
name: agent-harness-design
description: Agent Harness 工程化设计与产品化:14 机制+30 反模式+Loop+多 Agent 图+5 轴. 触发:做 Agent/设计/评审/加新机制/做自动化 Loop/升级多 Agent.
license: MIT
---

# Agent Harness Design

**核心立场**:Agent = Model(LLM) + Harness(让模型能在某环境工作的操作系统)。Agency 来自模型训练,不是来自外部代码编排。一个能工作的 Agent 产品必须有完整的 Harness。

## 高层视角选型表

先把 Agent 系统拆成 5 个**主分类**(walkinglabs L02 §"What a Harness Actually Is")。**正交性声明**:5 个主分类大致正交,但单个机制可同时跨多视角——做选型时先选主分类,再考虑跨轴副作用。工程上的判断都从这张表开始。

| 视角 | 看什么 | 用哪个 reference | 跨轴副作用(常见越界) |
|---|---|---|---|
| **Instructions / 指令体系** | `AGENTS.md` / `CLAUDE.md` / `.cursorrules` 等仓库即规范文件;规则优先级与可变层数 | [`02-checklist.md` §10 Skills System](references/02-checklist.md) + [`02-checklist.md` §1 Agent Loop](references/02-checklist.md) | **Skills System 同时是 Tools 加载路径**(`load_skill` 是工具调用);**Agent Loop 同时涉及 Instructions 注入**(system prompt 组装) |
| **Tools / 工具表面** | schema/handler/policy 三合一、并发调度、错误反传、MCP 接入 | [`02-checklist.md` §2 §3](references/02-checklist.md) + [`03-antipatterns.md` L4 L5](references/03-antipatterns.md) | **Hooks 同时是 Feedback**(权限审批反馈);**MCP Connectors 同时是 Environment**(网络依赖管理) |
| **Environment / 环境** | 运行时(本地 / 容器 / Worktree)、依赖锁(pyproject.toml / package.json)、版本固定(.nvmrc / .python-version)、可复现性 | [`02-checklist.md` §1](references/02-checklist.md) + [`04-production.md` §轴5 安全与权限](references/04-production.md) | 与 Tools 的边界:MCP 既是 Tools 接入也是 Environment 依赖 |
| **State / 状态** | 会话 transcript、跨重启的事实、进度文件、append-only 持久化与 head anchor | [`02-checklist.md` §6 Memory System](references/02-checklist.md) + [`03-antipatterns.md`](references/03-antipatterns.md) | **Audit & Hash Chain 同时是 Feedback**(告警);**Memory 召回是 Feedback 循环**(query → 召回 → 注入,非纯 State 读取);**Context Compact 严格说同时跨 State + Tools**(四步管道是 messages[] 状态管理,本身也是 4 个操作) |
| **Feedback / 反馈** | 验证命令(test / lint / type-check)、Goal/Evaluator 分离、独立评估器 | [`02-checklist.md` §5](references/02-checklist.md) + [`06-loop-engineering.md` §Generator/Evaluator](references/06-loop-engineering.md) | **Context Compact 不在本视角**(本质是 State+Tools);**Memory 召回部分在本视角** |

> **框架中立**:两个上游(walkinglabs L02 五子系统 / WanLanglin §1.2 三大支柱)对视角的划分不同——walkinglabs 强调"哪些设施决定了 Agent 的能力实现率",WanLanglin 强调"该把工程时间投到哪几块";本表用 walkinglabs 的五子系统组织路由,引用源在 [`05-source-synthesis.md`](references/05-source-synthesis.md)。

## When to use

触发此 skill 的四类场景:

1. **从 0 设计一个 Agent 产品/系统**——用户说"我要做一个 Agent"、"帮我设计这个 Agent 的架构"、"规划一个 Agent 团队"
2. **评审/诊断已有 Agent 设计**——用户说"这个 Agent 设计得怎么样"、"为什么我的 Agent 不稳"、"这个架构有什么问题"
3. **给已有 Agent 加新机制**——用户说"加多 Agent 协作"、"接 MCP"、"加记忆"、"加权限 Hook"、"加上下文压缩"
4. **自动化 / 升级到图**——用户说"让 Agent 自己跑起来"、"我要 Loop 不是单次对话"、"把单 Agent 拆成多 Agent 团队"、"接 cron / webhook / 定时任务"

**不**适用:纯模型训练/SFT/RLHF、纯 prompt engineering(无 harness 决策)、纯前端 UI 设计。

## Quick start

1. 先读 [`references/01-mindset.md`](references/01-mindset.md) 5 分钟——理解 Model + Harness 范式与三大根本张力。
2. 按你的场景,跳到 `## Workflow` 对应段,按步骤落地。
3. 完成后用 [`references/03-antipatterns.md`](references/03-antipatterns.md) 自检,过完所有"❌ 不要做"清单。
4. 上线前用 [`references/04-production.md`](references/04-production.md) 跑五轴检查(API / 错误 / 可观测 / 性能 / 安全)。
5. 若涉及自动化 / Loop / 多 Agent 图 / 选 Frontier 产品范式,先读 [`references/06-loop-engineering.md`](references/06-loop-engineering.md) 或 [`references/07-graph-engineering.md`](references/07-graph-engineering.md);需要横向对比主流产品设计,看 [`references/08-frontier-designs.md`](references/08-frontier-designs.md)。

## Core paradigm

**Agent = Model + Harness**。Model 是大脑(LLM),Harness 是让大脑能持续工作、使用工具、保持上下文、交付文件、接受治理的操作系统。

**Harness = Tools + Knowledge + Observation + Action Interfaces + Permissions**。但从工程视角,Harness 由 14 个核心机制构成:

1. **Agent Loop** — `while True` + `tool_use` + `tool_result`,循环恒定
2. **Tool Registry / Dispatch** — 单一真源,加工具不改循环
3. **Deferred Tool Loading** — 工具先列目录,schema 按需展开
4. **Permission / Hooks** — 三态闸门(allow/ask/deny)+ 4 事件扩展点
5. **Context Compact** — 四步压缩管道(持久化→剪裁→替换→摘要)
6. **Memory System** — 跨会话知识,workspace / user / remote 三层所有权
7. **SubAgent / Team** — 上下文隔离 + 持久队友 + 共享黑板
8. **Task System** — 文件持久化任务图 + 阻塞 + 原子认领
9. **MCP Connectors** — 外部工具命名空间汇入工具池
10. **Skills System** — `SKILL.md` 目录 + 按需全文加载
11. **Audit & Hash Chain** — append-only 证据流 + 防篡改链
12. **Session & Runtime** — UI 不跑 agent,session 可恢复,运行时可重建
13. **Multi-Provider Adapter** — 协议差异归一,Loop 只看中性类型
14. **Event-Driven Bus** — 订阅(只读) vs 决策(可动手)两条管道

完整机制表与"为什么 / 在哪 / 如何验证"见 [`references/02-checklist.md`](references/02-checklist.md)。

## Workflow

### 场景 A:从 0 设计一个 Agent 系统

1. **明确目标域与边界**——这个 Agent 解决什么?不解决什么?(单域 vs 通用)

   **会话生命周期 16 步**(参考 walkinglabs root README §"The Agent Session Lifecycle",不在 L02):每个 Agent 会话从启动到结束都走这条流水线;工程上各步分别对应 02-checklist 的不同机制。

   > **步骤名为本 skill 概念化标注**:walkinglabs 原始描述是动作式(Agent reads X / Agent runs Y),**结构**(4 阶段 × N 步)与上游一致,但**具体步骤名**(Bootstrap / Verify / Model turn 等)为本 skill 对原 16 步的概念抽象,非 walkinglabs 原话。引用时按本表读,做实操再回原 README。

   ```text
   START (1-5):
     [1] Bootstrap
     [2] Verify
     [3] Open session
     [4] Load context
     [5] Seed plan/todos

   SELECT (6-7):
     [6] Listen
     [7] Gate

   EXECUTE (8-11):
     [8] Model turn
     [9] Tool dispatch
     [10] Hooks (post-tool)
     [11] Append messages

   WRAP UP (12-16):
     [12] Settle
     [13] Audit
     [14] Compact
     [15] Continue
     [16] End session
   ```

   对应 `## Quick start` 的 5 步:Quick Start 1-5 对应 START 1-5(心智与边界);Workflow 场景 A 步骤 2-8 对应 SELECT 6-7 + EXECUTE 8-11(工具/记忆/权限/上下文/审计);上线前 04-production 对应 WRAP UP 12-16(可观测/性能/安全)。

2. **选择 Loop 形态**——单进程 vs Sidecar(Sidecar 适合桌面/服务端);CLI vs TUI vs Web vs GUI
3. **设计 Tool Registry**——内部工具(只读→写→网络→执行)、Skills、MCP 三层合一,统一命名
4. **定义 Memory 边界**——workspace(项目事实)/ user(偏好)/ remote(profile)三层,所有权清晰
5. **设计权限闸门**——DENY 永不弹窗;ASK 走用户审批;ALLOW 默认可执行
6. **设计上下文预算**——最大工具输出上限、压缩阈值、Skills 懒加载
7. **设计审计**——JSONL append-only + SHA256 哈希链 + head anchor(防删尾)
8. **画出"为什么这么设计"的一页图**——六层架构(UI / Agent / 工具 / 扩展 / 记忆 / 治理)责任清晰

验证:`scripts/verify.py`(如 learn-workbuddy 范式)+ 离线 mock 跑通 + 真实 key 跑通 demo 套件

### 场景 B:评审/诊断已有 Agent 设计

1. **跑一遍反模式清单** [`references/03-antipatterns.md`](references/03-antipatterns.md)——**30 项过完**(实际为 30 个:范式层 6 + Loop 层 8 + 上下文层 5 + 多 Agent 层 4 + 运营层 5 + Graph 层 2),标红项就是问题
2. **检查 Loop 是否恒定**——`while True` 是否被改写过?有没有 if-else 分支插在循环体?
3. **检查 Tool Registry 是否单一真源**——schema/handler/policy 是否分开?有没有三处定义?
4. **检查权限是否三段式**——decide / resolve / run 是否分开?是否有 DENY 被覆盖的可能?
5. **检查上下文四步管道**——持久化 / 剪裁 / 替换 / 摘要是否都实现?顺序对吗?
6. **检查审计链是否带 head anchor**——只算哈希链不够,要防"删尾"
7. **检查多 Agent 通信是否隔离**——子 Agent 是否会污染主窗口?Team 通信是否有边界?

输出格式:`{机制名} → {状态: ✅ / ⚠️ / ❌} → {问题描述} → {修复建议}`

### 场景 C:给已有 Agent 加新机制

1. **确认 Loop 不变**——新机制永远通过 dispatch map / hooks / system prompt 注入,不写进循环体
2. **从最小子集开始**——不要一次加完整套。先加 Loop 必备(tools + dispatch),再加上下文(compact),再加安全(permission)
3. **遵循渐进顺序**:`agent_loop` → `tool_dispatch` → `permission` → `hooks` → `todo_write` → `subagent` → `skills` → `context_compact` → `memory` → `task_system` → `multi_agent` → `mcp` → `audit` → `production_check`
4. **每加一个机制就跑回归**——离线 mock + 真实 key 两套都跑,确保旧路径不退化
5. **加完后用 [`references/05-source-synthesis.md`](references/05-source-synthesis.md) 校准**——三个上游资源各自覆盖了什么,避免重复造轮子

### 场景 D:自动化 / 升级到 Loop / 多 Agent 图

1. **判定是否真要自动化**——参照 [`references/06-loop-engineering.md` §何时用 / 何时不用](references/06-loop-engineering.md),满足 ≥ 1 条"何时用"且不命中"何时不用"才走 Loop 工程路径
2. **选 Loop 形态**——读 [`06-loop-engineering.md` §4 种循环](references/06-loop-engineering.md)(Goal-driven / Timer-driven / Maker-Checker / Event-driven),匹配你的触发源
3. **确认是否需要 Graph**——读 [`references/07-graph-engineering.md` §5 评估标准](references/07-graph-engineering.md)(任务复杂度 / 并行收益 / 责任可分 / 评审带宽 / 失败兜底),**满足 ≥ 3 条才上 Graph**
4. **落实 6 原语**——`Automations` / `Worktrees` / `Skills` / `Connectors` / `Sub-agents` / `External State`([`06-loop-engineering.md` §6 原语](references/06-loop-engineering.md))缺一不可
5. **自检 4 Silent Costs**——Verification Debt / Comprehension Rot / Cognitive Surrender / Token Blowout([`06-loop-engineering.md` §4 Silent Costs](references/06-loop-engineering.md))各自准备治理动作
6. **横向对比 Frontier**——如要做选型 / 借鉴,读 [`08-frontier-designs.md`](references/08-frontier-designs.md) Pi / Claude Code / Codex / DeepSeek 4 种设计哲学与 12 维评估框架(只用框架名,具体单元格数据见原仓库)
7. **Generator / Evaluator 分离**——Loop 内核必须有独立评估器,见 [`06-loop-engineering.md` §Generator/Evaluator Separation](references/06-loop-engineering.md)

**为何本场景单独成段**:`06 / 07` 引用文件本身已自洽,但 `SKILL.md` 之前未给场景 D 提供 step-by-step 入口。本段修复 SKILL.md 的 4 类场景承诺闭环。

**与场景 C 的区别**:场景 C 加单机制(短时);场景 D 升级架构(天 / 周级,涉及 Loop 持久化、Worktree、多 Agent 通信、External State)。

## Federation(可选集成)

📦 **生产落地**:要把本 skill 的设计哲学落到真实生产环境的 Pi Coding Agent 时,`pi-coding-agent` v0.83.0+ 的具体 API(`createAgentSession` / `defineTool` / `pi.on` / `session.subscribe` / SSE streaming)详见上游 **`dg-piagent`** skill(从仓库根 `docs/awesome-skills.md` 入口)。**本 skill 保持 vendor-neutral**——只讲 harness 设计哲学,不绑定 SDK 版本;`dg-piagent` 维护 SDK 版本化的具体实现。选型时先读本 skill 决定走哪几条主路径,再装 `dg-piagent` 落地到 Pi 运行时。

## References

按使用阶段递进,按需加载。

### 先读

- [`references/01-mindset.md`](references/01-mindset.md) — **必读**:Model + Harness 范式、三大根本张力(上下文 vs 信息 / 自主 vs 安全 / 成本 vs 复杂度)、内核+叠加 Loop、两条事件管道

### 按需

- [`references/02-checklist.md`](references/02-checklist.md) — 14 个机制清单(机制 / 为什么 / 在哪章 / 如何验证),从 0 设计与评审都查这张表
- [`references/03-antipatterns.md`](references/03-antipatterns.md) — **30 个反模式**(范式层 6 + Loop 层 8 + 上下文层 5 + 多 Agent 层 4 + 运营层 5 + Graph 层 2;每条 错 / 对 / 为什么错),设计完成与加新机制后必跑自检
- [`references/04-production.md`](references/04-production.md) — 产品化落地 5 轴(API 化 / 错误处理 / 可观测性 / 性能 / 安全),上线前必跑
- [`references/06-loop-engineering.md`](references/06-loop-engineering.md) — 自动化 Loop:6 原语、4 silent costs、generator/evaluator 分离
- [`references/07-graph-engineering.md`](references/07-graph-engineering.md) — 多 Agent 图:4 部件、3 结构性失败、orchestration tax
- [`references/08-frontier-designs.md`](references/08-frontier-designs.md) — 4 个 Frontier 产品(Pi / Claude Code / Codex / DeepSeek)的横向对比与迁移清单

### 延伸

- [`references/05-source-synthesis.md`](references/05-source-synthesis.md) — 五个上游资源的独有贡献 + 机制 × 来源映射表 + 延伸阅读指针(Grove / Anti-Distillation),做交叉校准用
