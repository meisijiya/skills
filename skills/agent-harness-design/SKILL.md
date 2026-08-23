---
name: agent-harness-design
description: 指导 Agent 系统的工程化设计与产品化落地：核心范式、机制清单、反模式与上线检查。触发:做 Agent、设计/评审 Agent 架构、加新机制。
license: MIT
---

# Agent Harness Design

**核心立场**:Agent = Model(LLM) + Harness(让模型能在某环境工作的操作系统)。Agency 来自模型训练,不是来自外部代码编排。一个能工作的 Agent 产品必须有完整的 Harness。

## When to use

触发此 skill 的三类场景:

1. **从 0 设计一个 Agent 产品/系统**——用户说"我要做一个 Agent"、"帮我设计这个 Agent 的架构"、"规划一个 Agent 团队"
2. **评审/诊断已有 Agent 设计**——用户说"这个 Agent 设计得怎么样"、"为什么我的 Agent 不稳"、"这个架构有什么问题"
3. **给已有 Agent 加新机制**——用户说"加多 Agent 协作"、"接 MCP"、"加记忆"、"加权限 Hook"、"加上下文压缩"

**不**适用:纯模型训练/SFT/RLHF、纯 prompt engineering(无 harness 决策)、纯前端 UI 设计。

## Quick start

1. 先读 [`references/01-mindset.md`](references/01-mindset.md) 5 分钟——理解 Model + Harness 范式与三大根本张力。
2. 按你的场景,跳到 `## Workflow` 对应段,按步骤落地。
3. 完成后用 [`references/03-antipatterns.md`](references/03-antipatterns.md) 自检,过完所有"❌ 不要做"清单。
4. 上线前用 [`references/04-production.md`](references/04-production.md) 跑五轴检查(API / 错误 / 可观测 / 性能 / 安全)。

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
2. **选择 Loop 形态**——单进程 vs Sidecar(Sidecar 适合桌面/服务端);CLI vs TUI vs Web vs GUI
3. **设计 Tool Registry**——内部工具(只读→写→网络→执行)、Skills、MCP 三层合一,统一命名
4. **定义 Memory 边界**——workspace(项目事实)/ user(偏好)/ remote(profile)三层,所有权清晰
5. **设计权限闸门**——DENY 永不弹窗;ASK 走用户审批;ALLOW 默认可执行
6. **设计上下文预算**——最大工具输出上限、压缩阈值、Skills 懒加载
7. **设计审计**——JSONL append-only + SHA256 哈希链 + head anchor(防删尾)
8. **画出"为什么这么设计"的一页图**——六层架构(UI / Agent / 工具 / 扩展 / 记忆 / 治理)责任清晰

验证:`scripts/verify.py`(如 learn-workbuddy 范式)+ 离线 mock 跑通 + 真实 key 跑通 demo 套件

### 场景 B:评审/诊断已有 Agent 设计

1. **跑一遍反模式清单** [`references/03-antipatterns.md`](references/03-antipatterns.md)——**24 项过完**,标红项就是问题
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

## References

按设计阶段递进,按需加载:

- [`references/01-mindset.md`](references/01-mindset.md) — **必读**:Model + Harness 范式、三大根本张力(上下文 vs 信息 / 自主 vs 安全 / 成本 vs 复杂度)、内核+叠加 Loop、两条事件管道
- [`references/02-checklist.md`](references/02-checklist.md) — 14 个机制清单(机制 / 为什么 / 在哪章 / 如何验证),从 0 设计与评审都查这张表
- [`references/03-antipatterns.md`](references/03-antipatterns.md) — **24 个反模式**(错 / 对 / 为什么错),设计完成与加新机制后必跑自检
- [`references/04-production.md`](references/04-production.md) — 产品化落地 5 轴(API 化 / 错误处理 / 可观测性 / 性能 / 安全),上线前必跑
- [`references/05-source-synthesis.md`](references/05-source-synthesis.md) — 三个上游资源(learn-claude-code / learn-workbuddy / dg-ai-notes)的独有贡献 + 机制 × 来源映射表,做交叉校准用
