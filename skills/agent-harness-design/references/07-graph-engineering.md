# 07 · Graph Engineering — 多 Agent 图的设计与失败

> 本文件讲"如何把单 Loop 升级为多 Agent 协作图"。读完 5 分钟,理解 Graph 的 4 部件、3 结构性失败、orchestration tax。

## 一句话 / 核心概念

**Graph = 4 个相互正交的部件**:Nodes(执行者)、Edges(谁叫谁)、Shared State(共享黑板)、Routing Rules(分发规则)。任何"多 Agent"系统都可以拆成这 4 部件的组合,差异只在密度。

```
Nodes      — 谁执行(每个 node 通常是一个 Loop,有时是 deterministic code)
Edges      — 谁调用谁(directed,不一定双向)
Shared State — 跨 node 共享的事实(TaskList / Plan / 状态摘要)
Routing Rules — 消息 / 任务分发到哪个 node 的规则
```

> **反直觉**:图的"复杂度"不在 Nodes 数,而在 Edges × Shared State 的乘积。Nodes 多但 Edges 稀疏、Shared State 简洁 = 可控;Nodes 少但 Edges 密集、Shared State 复杂 = 失控。

## 4 层堆叠

Agent 系统从单进程升级到图,需要 4 层能力堆叠,缺哪一层就掉哪一层的坑:

| 层 | 解决的问题 | 没有这层的代价 |
|---|---|---|
| **Prompt** | 单次对话的指令传递 | 模型听不懂任务 |
| **Context** | 单次对话的信息容量 | 模型记不住上下文 |
| **Loop** | 单次任务的执行控制 | 任务跑不通 |
| **Graph** | 多任务的并行 / 串行编排 | 复杂任务拆不开 |

> **堆叠顺序**:**Prompt → Context → Loop → Graph**。跳层必败——没有 Loop 直接上 Graph,等于让一群裸奔的 LLM 互相喊话。没有 Context 直接上 Graph,等于让没有记忆的 Agent 协同,每次都从零开始。

## 3 结构性失败

多 Agent 图特有的 3 类失败(单 Loop 不会有):

| 失败 | 表现 | 根因 | 预防 |
|---|---|---|---|
| **Goodhart** | 子 Agent 都"完成"了,但总目标失败 | 子目标与总目标脱钩 | 子目标必须由总目标派生;独立 `goal_gate` 评总目标 |
| **Blindness Upward** | 子 Agent 看不到上层 context,做出局部最优决策 | 信息流单向 | 上层关键约束(成本上限 / 截止时间 / 不可触碰资源)必须显式 push 给每个子 Agent |
| **Conflict** | 多个子 Agent 互相否决对方的产出 | 没有仲裁者 | Shared State 必须有单一权威(任务系统 / 黑板 / 共享 memory);任意冲突走权威 |

> **共性**:3 类失败都不是"Agent 不够聪明",是**图的拓扑错了**。修复方法是改 Routing Rules / Edges / Shared State,不是给 Agent 加更长的 prompt。

## Anchors

**Anchors = 把 Loop 钉到真实世界的接缝点**。一个没有 anchor 的 Loop 永远在幻觉里打转,产出再漂亮也没人接。

| Anchor 类型 | 接的真实世界 | 例子 |
|---|---|---|
| **Test runner** | 代码确实能跑 | pytest / go test / jest |
| **Lint / type checker** | 代码符合规范 | eslint / mypy / clippy |
| **Git status** | 改动真在仓库里 | `git diff` / `git status` / `git log` |
| **External API response** | 数据真的来自上游 | `curl` 真实接口 / 跑 fixture |
| **User explicit signal** | 用户确实要这个 | 人类手动 approve / `goal_gate` 通过 |

> **判断**:一个 Loop 的产出如果全是"我以为……"而不是"我验证过……",说明它缺 anchor。Anchor 不是 nice-to-have,是 Loop 的可信度基础设施。

## Orchestration Tax

**你的注意力是唯一串行资源**。并行 Agent 可以把产出放大 N 倍,但你**评审产出**的速度是固定的——N 份产出 vs 1 份注意力,产出超出评审带宽的部分是负价值。

| 维度 | 计算 |
|---|---|
| 并行度上限 | = 你的评审带宽(产出/单位时间) |
| 评审带宽的硬约束 | 工作日 8 小时里能严肃评审的产出数(典型 3-5 个 PR) |
| 超出代价 | 模型复刻同一份错误的概率 ≈ 模型独立出错的概率,N 份产出错的概率近似独立 |

> **实操**:开 5 个并行 Agent 跑同一任务,如果你的评审带宽只能看 1 份,期望看到的"最佳产出"和开 1 个 Agent 没有区别,只是多了 4 份 noise。如果必须并行,要让子 Agent 跑**不同子问题**,产出在评审层才互补,不是同一问题 5 次。

## Graph vs Workflow

| 维度 | Graph | Workflow |
|---|---|---|
| 决策权 | LLM 在 routing 决定下一步 | 代码 if-else 决定下一步 |
| 状态 | Shared State 跨 node 可变 | 步骤间 immutable data |
| 失败模式 | 3 结构性失败(Goodhart / Blindness / Conflict) | DAG 编译错误 / 死锁 |
| 适合 | 任务模式未完全确定、需模型判断分叉 | 任务模式固定、需确定性 |
| 成本 | LLM 调用多(token 贵) | 代码执行多(快且便宜) |

> **判定**:你能画清楚每一步的 DAG → 用 Workflow;你只能说"大概是这样,但需要模型根据实际情况调整" → 用 Graph。前者追求可重现,后者追求适应性。

## 何时用 / 何时不用

**5 评估标准**(满足 ≥ 3 才考虑上 Graph):

| # | 标准 | 描述 |
|---|---|---|
| 1 | **任务复杂度** | 单 Loop 跑不下来(模型顾不过来 / token 不够 / 步骤太多) |
| 2 | **并行收益** | 子任务可并行且并行后总时长显著缩短(>2x) |
| 3 | **责任可分** | 子任务的责任边界清晰,产出可独立 review |
| 4 | **评审带宽** | 你的注意力能 cover 多份产出(否则是 orchestration tax 负价值) |
| 5 | **失败兜底** | 任意子任务失败可优雅降级(子任务重试 / 总目标 partial credit) |

**不满足任意 1 条就不上 Graph**:单 Loop + 更好的工具 + 更长的 Context 通常更便宜。

## 引用与致谢

本文件提炼自 `walkinglabs/learn-harness-engineering` L14 §Take the Graph Apart + §Three Structural Failures + §Anchors + §Orchestration Tax;`dg-ai-notes.pages.dev` 21-multi-agent.md SDK 视角的 5 个 multi-agent 模式(multi-session / runtime switch / subagent tool / handoff / fork)。所有内容均为重新表述,不复制上游逐字原文。

## 附录 · 5 种 multi-agent 模式(SDK 视角)

`dg-ai-notes.pages.dev` 21-multi-agent.md 把多 Agent 协作拆成 5 种实现模式,各种 Graph 设计都可以归到其中之一或多者组合:

| # | 模式 | 描述 | 适用 |
|---|---|---|---|
| 1 | **multi-session** | 多个独立 session,各自有完整 messages[],通过外部 channel 通信 | 长期独立任务,需要各自 memory |
| 2 | **runtime switch** | 同一个 session,根据当前任务切换到不同 runtime / 模型 | 模型路由策略化 |
| 3 | **subagent tool** | 把 sub-agent 作为 tool,主 Agent 像调工具一样调 | 主从结构清晰的场景 |
| 4 | **handoff** | 把控制权从一个 Agent 完全交给另一个,原 Agent 进入 sleep | 不同阶段任务由不同专长 Agent 处理 |
| 5 | **fork** | 从某个节点复制状态,开新 branch 独立跑 | 需要并行探索多种方案 |

> **选型**:5 种模式不互斥。一个复杂的 Graph 可能同时用 subagent tool + handoff(sub-agent 完成某段后 handoff 给下一个专家 Agent)。关键是:每种模式都有自己的失败模式,别混着用不熟悉的。

## 附录 · 图的可调试性

图比 Loop 难调试,因为状态分布在多个 node + 共享 state。3 个调试技巧:

1. **强制落盘所有跨 node 消息**——Graph 的"看不见的传话"是 silent failure 的高发区
2. **每节点独立 transcript**——子 Agent 的 messages[] 必须能独立查看,不要只在主 session 里看
3. **Routing 决策可见**——节点分发到哪个 node 的逻辑必须可观测,否则失败时不知道消息去了哪