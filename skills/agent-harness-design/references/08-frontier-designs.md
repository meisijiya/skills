# 08 · Frontier Designs — 4 个主流 Agent 产品的横向对比

> 本文件对比 Pi / Claude Code / Codex / DeepSeek 四个主流 Agent 产品的设计取舍,提炼每个产品"可以学什么"。
>
> ⚠️ **License 摘要**:本文件引用 `walkinglabs/learn-harness-engineering` 的 `docs/zh/harness-designs/` 目录(MIT,可 re-derivation)以及 `WanLanglin/-awesome-cc-harness` §16.1 12 维对比("All Rights Reserved / viewing only",**禁止复制**)。WanLanglin 部分只引用章节编号与表格维度名称(Claude Code / Cursor / GitHub Copilot × 12 维度框架),不复制表格内容;WanLanglin 的 12 维数据点**均为单一来源,未交叉复现**,引用前请回原文核对。

## 立场声明

**本节是观察样本,不是推荐**。所有产品在 2026-08 时刻被观察,API 演进快,引用前请核对最新状态。

- 本节不替任何产品站台,不暗示"哪个最好"
- 本节不做选型推荐;选型应基于你的具体场景与团队约束
- 所有数据点来自公开仓库、SDK 文档或可重现的 demo;未在生产环境实测
- 产品 API 变化频繁,本节**最多 6 个月内有效**,超期请回到对应仓库读最新版本

**为什么观察 4 个**:这 4 个产品在 2026-08 时刻代表了 Agent 工程 4 种最显著的设计哲学;其他产品(Cursor、Copilot、Aider、Continue 等)各有取舍,但 4 种主哲学已被这 4 个覆盖,其他可在 12 维表里横向对照。

## 一句话 / 为什么对比 4 个产品

四个产品代表了 Agent 工程的 4 种设计哲学:

| 产品 | 哲学 | 一句话 |
|---|---|---|
| **Pi** | minimal core + programmable extensions | 极简内核,所有功能靠 extension 加 |
| **Claude Code** | 完整运行时 + 多层优化 | 大而全,把性能与治理做到极致 |
| **Codex** | AGENTS.md + Worktree + spawn_agent | 文件即配置,worktree 即沙箱 |
| **DeepSeek** | everything is a plugin + capability seam | 一切皆插件,能力缝隙即扩展点 |

> **对比目的不是排名,而是看清 4 种取舍的代价**。A 产品选了"极简",代价是用户要自己写 extension;B 产品选了"完整",代价是包体大、扩展点固化。本节把这 4 个代价摆出来,让你选型时心里有数。

**对比的方法学**:
- 只看**设计哲学**与**取舍代价**,不做性能基准测试——基准随版本变化,哲学相对稳定
- 每个产品配一段"可迁移到自己的 Harness 的设计"——这是本节的实用产出
- 跨产品对比用 12 维统一维度表(见下);每个产品的子段只讲这个产品特有的取舍
- 不预测"未来哪个产品会赢"——产品演进受市场因素影响,本节刻意不覆盖

## Pi — minimal core + programmable extensions

**设计哲学**:内核越小越好,所有非核心功能走 extension。

**核心取舍**:

| 取舍 | Pi 的选择 | 代价 |
|---|---|---|
| 内核大小 | 极简(几十行 Loop + 工具调度) | 用户得自己写 extension 来加大部分功能 |
| 扩展点 | extension API 完整 | extension 写错可能 crash 内核 |
| 上下文管理 | 基础截断 + 摘要 | 没有 5 层压缩那样的极致优化 |
| 工具系统 | flat dispatch map | 大工具库性能差 |

**适合**:喜欢写 extension 的开发者、研究型项目、需要深度定制的小团队。

## Claude Code — 完整运行时 + 5 层压缩 + 4 扩展机制

**设计哲学**:大而全,把性能、安全、治理都做到极致,用户几乎不需要碰内核。

**核心取舍**:

| 取舍 | Claude Code 的选择 | 代价 |
|---|---|---|
| 内核大小 | 大(完整运行时 + 大量内置机制) | 包体大、二次开发需学大量概念 |
| 扩展机制 | 4 种事件(PreToolUse / PostToolUse / UserPromptSubmit / Stop) | 扩展点固化,新场景得 hack |
| 上下文压缩 | 5 层压缩(截断 / 去重 / 修剪 / 占位符 / 摘要) | 实现复杂,bug 难定位 |
| 审计 | append-only + SHA256 + head anchor | 落盘开销大,需清理策略 |
| 多 Agent | SubAgent + Team 完整支持 | 通信协议复杂 |

**适合**:企业级生产环境、对安全与审计有强要求的项目、需要多 Agent 协作的复杂任务。

## Codex — AGENTS.md directory page + Worktree + spawn_agent

**设计哲学**:用文件系统作为 Agent 的协作介质,worktree 作为天然沙箱。

**核心取舍**:

| 取舍 | Codex 的选择 | 代价 |
|---|---|---|
| 配置文件 | `AGENTS.md`(目录级 instruction page) | 用户要会写 markdown instruction |
| 沙箱 | git worktree per task | 依赖 git,worktree 数量爆炸时磁盘压力大 |
| 多 Agent | `spawn_agent()` 同步调用 | 进程模型,不便异步协作 |
| 任务系统 | 文件系统持久化 | 重命名 / 移动 task 需保持 ID 稳定 |

**适合**:代码任务为主的项目、需要 git 沙箱的 PR 评审流程、喜欢"一切皆文件"哲学的团队。

## DeepSeek — everything is a plugin + capability seam

**设计哲学**:能力边界 = 插件边界,每个能力缝隙都是扩展点。

**核心取舍**:

| 取舍 | DeepSeek 的选择 | 代价 |
|---|---|---|
| 内核 | 极简 + 大量插件 | 插件版本兼容性问题 |
| 扩展点 | capability seam(每个能力边界都可换) | 文档需要描述每个 seam,新手不友好 |
| 模型路由 | 内置多模型 + 智能路由 | 路由策略不透明,debug 难 |
| 多 Provider | 原生 multi-provider | provider 差异归一复杂 |

**适合**:多模型场景、对模型切换有需求的项目、需要快速实验不同 LLM 的研究团队。

## 12 维 Claude Code vs Cursor vs Copilot(WanLanglin §16.1)

> ⚠️ **License 警告**:本节引用 `WanLanglin/-awesome-cc-harness` §16.1(许可证禁止 copy / modify / distribute / fork / clone)。本 skill **只引用章节编号 + 12 维度框架名称**,**不复制** §16.1 的具体对比单元格内容。读者需自行访问 https://github.com/WanLanglin/-awesome-cc-harness 在线查看 §16.1 全文。

WanLanglin §16.1 把 Claude Code / Cursor / GitHub Copilot 三个主流编码助手做 12 维对比。该章节给出的 12 维度框架名称(WanLanglin 命名,**只引用维度名,不复制单元格内容**):

1. 运行环境(Runtime Environment)
2. 交互模式(Interaction Mode)
3. Agent Loop
4. 工具系统(Tool System)
5. 权限模型(Permission Model)
6. Hook 系统(Hook System)
7. 上下文管理(Context Management)
8. 多 Agent(Multi-Agent)
9. MCP 支持(MCP Support)
10. 开源可见度(Source Visibility)
11. 评估集成(Evaluation Integration)
12. 市场份额(Market Share)

> **12 维视角的价值**:这 12 项不是简单的"谁有谁无",而是工程权衡的具体维度——每个维度背后都有 OpenDev 论文 / 源码逆向的市场验证或可观察的设计取舍。**做自己的 Harness 时拿这 12 个维度做自评**——你打算在哪几项上下注?哪几项可以外包?Claude Code 在 Hook 系统、上下文管理、评估集成上对外可分析(512K LOC 全公开),适合"先学后改";Cursor 的代码库索引 + 8 并行 Agent 在编辑器内体验上更强;Copilot 仍在反应式补全 + Agent Mode 之间切换,跟 GitHub 权限紧绑。具体单元格数据读者回原文 §16.1 核对。
>
> **自评替代**:本 skill **不复制** §16.1 单元格数据,自研 Harness 时用同文件 **§5 子系统评分维度**(walkinglabs L02 五子系统,各 0-5 分)代替 12 维做自评——5 子系统分数足够指导设计决策;12 维框架留给横向选型(买 / 自研 / 二次开发)决策,不需回 WanLanglin 原仓库。

## 5 子系统评分维度

按本 skill 的 5 子系统视角,对每个产品做 1-5 分打分(主观,引用前请自行核验):

| 产品 | 工具生态 | 上下文工程 | 子 Agent | 持久化 | 扩展点 |
|---|---|---|---|---|---|
| **Pi** | 3 | 3 | 2 | 3 | 5 |
| **Claude Code** | 5 | 5 | 5 | 4 | 4 |
| **Codex** | 4 | 4 | 3 | 5 | 3 |
| **DeepSeek** | 4 | 4 | 4 | 3 | 5 |

> **评分说明**:分数反映"该子系统在该产品上的成熟度",不是产品质量排名。例如 Pi 扩展点 5 分因为 extension API 完整;Claude Code 工具生态 5 分因为工具库最丰富。

## 每个产品的"学什么"迁移清单

| 产品 | 可迁移到自己的 Harness 的设计 |
|---|---|
| **Pi** | minimal core 的边界划法——"什么是必须的,什么是 extension"。避免一开始把所有功能塞进内核 |
| **Claude Code** | 5 层压缩管道、3 段式权限、head anchor 审计、subscribe vs on 两条事件管道 |
| **Codex** | 文件系统作为协作介质(`AGENTS.md` / `.tasks/` / JSONL);worktree 作为天然沙箱 |
| **DeepSeek** | capability seam 思维——把每个能力边界都设计成可替换的接缝,便于未来换实现 |

> **迁移 ≠ 复制**:每个产品的设计背后都有它的产品定位与历史包袱。直接复制某个机制到自己的 Harness 上,常常因为 context 不同而水土不服。先理解机制要解决的问题,再决定要不要在自己的 Harness 里解决同样的问题。

## 引用与致谢

本文件综合 `walkinglabs/learn-harness-engineering` `frontier-designs/` 目录下对 Pi / Claude Code / Codex / DeepSeek 的逐个分析;`WanLanglin/-awesome-cc-harness` §16 12 维竞品对比(Claude Code vs Cursor vs Copilot)。所有内容均为观察提炼与重新表述,不复制上游逐字原文,引用前请核对各产品最新状态(API 演进快,2026-08 后可能有变动)。

## 附录 · 选型决策树

从需求出发选产品的最小决策路径:

```
Q1: 你需要极致定制内核?
  YES → Pi (或自研,基于 Pi 的 minimal core 思路)
  NO  → Q2

Q2: 你的任务以代码为主,且需要 PR 评审流程?
  YES → Codex (worktree + AGENTS.md 范式)
  NO  → Q3

Q3: 你需要频繁切换多个 LLM provider?
  YES → DeepSeek (multi-provider 原生 + capability seam)
  NO  → Q4

Q4: 你需要企业级安全/审计/治理?
  YES → Claude Code (5 层压缩 + 哈希链 + 三态权限 + 完整事件总线)
  NO  → 任意一个都行,看团队偏好
```

> **决策树不是推荐**——它只是把 4 个产品的核心取舍映射到 4 个常见需求。如果你的需求不在 Q1-Q4,可能需要回到 [`02-checklist.md`](../02-checklist.md)的 14 机制清单,自己选哪些机制要、要哪些机制不要,然后看哪个产品最匹配你的需求组合。

## 附录 · 自研 Harness 时怎么用本节

如果你的目标是"不直接用某个产品,而是从它们身上学设计",本节的用法:

1. **用 12 维表做自评**——你打算实现的 Harness,12 项里打算做哪几项?写到设计文档
2. **用 4 个产品段做参考实现**——每项设计查对应产品的实现,看它怎么权衡
3. **用 5 子系统评分维度做查漏**——你的设计里哪几项低于 3 分?要不要补?
4. **用迁移清单做取舍**——能"学到"的机制 vs "该学"的机制,后者才是你要做的

> **核心告诫**:**不要为了对齐某个产品而做错自己的 Harness**。每个产品的设计背后都有它的产品定位与历史包袱。直接复制某个机制到自己的 Harness 上,常常因为 context 不同而水土不服。