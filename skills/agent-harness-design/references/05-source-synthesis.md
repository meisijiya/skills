# 05 · Source Synthesis — 五个上游资源的独有贡献

> 本 skill 不是凭空写出来的,是从五个公开资源提炼融合而成。做交叉校准和引用时用。

## 五个资源定位对比

| 资源 | 视角 | 章节数 | 形态 | 独有贡献 |
|---|---|---|---|---|
| `shareAI-lab/learn-claude-code` | **CLI Agent 教学** | 17 + 17(中/日) | 教程 + 教学代码 | 范式定义("Agency 来自模型")、17 个机制章节化、单进程 Loop 演进路径 |
| `meisijiya/learn-workbuddy` | **桌面 Agent 工程** | 24 + docs | 教学代码 + 架构图 + 多 Provider | 六层架构、三大根本矛盾、Agent 角色分工、Sidecar 进程模型、多 Provider 适配、Hash Chain 审计 |
| `dg-ai-notes.pages.dev` | **生产 SDK 源码学习** | 10(源码)+ 7(实战) | 文档 + 代码片段 | 三层架构(`pi-ai` / `pi-agent-core` / `pi-coding-agent`)、内核+叠加 Loop、两条事件管道、SDK 视角 21-multi-agent 模式(独立于 M07)、二开起步检查清单(SKILL.md) |
| `walkinglabs/learn-harness-engineering` | **产品视角 Loop / Graph** | 14 节课 + 8 项目 + 15 种语言 | 教程 + 跨语言实现 | 5 子系统框架(Prompt / Context / Loop / Tools / Orchestration)、**会话生命周期 16 步**、**Loop Engineering (L13)**、**Graph Engineering (L14)**、**Frontier Designs**(Pi / Claude Code / Codex / DeepSeek) |
| `WanLanglin/-awesome-cc-harness` | **逆向 Claude Code 512K LOC** | 16 章 | 源码逆向 + 工程化总结 | **3 大支柱**(Context / Tools / Loop)、**ROI 量化证据**(+14% harness vs +3-5% model)、**3 级 Harness 成熟度**(L1/L2/L3)、**7 Continue Sites**、**工具分区算法**、**12 维竞品对比**、Grove + Anti-Distillation 伦理视角 |

## 机制 × 来源映射(本 skill 的 14 个机制从哪来)

| # | 机制 | 主源 | 辅源 | 独特之处 |
|---|---|---|---|---|
| 1 | Agent Loop | shareAI-lab(s01) | dg-ai-notes(M03) | shareAI-lab 给 30 行教学版,dg-ai-notes 给"内核+叠加"工程化 |
| 2 | Tool Registry / Dispatch | shareAI-lab(s02) | meisijiya(s02) | meisijiya 加 `concurrent_safe` 字段 |
| 3 | Deferred Tool Loading | shareAI-lab(s07) | meisijiya(s03) | 两边结构同构,meisijiya 加 session-scoped cache |
| 4 | Permission / Hooks | shareAI-lab(s03+s04) | meisijiya(s04) | meisijiya 加 WorkspaceScope 防三类逃逸 |
| 5 | Context Compact | shareAI-lab(s08) | meisijiya(s14) + dg-ai-notes(M08+M09) | shareAI-lab 给四步管道,meisijiya 加 DurableContextState,dg-ai-notes 给结构化摘要 6 section |
| 6 | Memory System | shareAI-lab(s09) | meisijiya(s10-s12) | meisijiya 给三层所有权(workspace/user/remote)清晰边界 |
| 7 | SubAgent / Team | shareAI-lab(s06+s13) | dg-ai-notes(references/sdk_doc/21-multi-agent.md) | dg-ai-notes 给 SDK 视角 5 个 multi-agent 模式拆分(multi-session / runtime switch / subagent tool / handoff / fork);教程 M07 讲设计哲学层 |
| 8 | Task System | shareAI-lab(s10) | meisijiya(s21) | shareAI-lab 教学版,meisijiya 用 SQLite 索引 JSONL |
| 9 | MCP Connectors | shareAI-lab(s14) | meisijiya(s17) | 二源一致:host 拥有权限,不信任 server 自报属性 |
| 10 | Skills System | shareAI-lab(s07) | 本仓库已有 skill 生态 | shareAI-lab 是 SKILL.md 协议的事实标准 |
| 11 | Audit & Hash Chain | meisijiya(s23) | shareAI-lab(无) | meisijiya 独有:head anchor 防删尾 |
| 12 | Session & Runtime | meisijiya(s05-s07) | shareAI-lab(无) | meisijiya 独有:Sidecar 进程模型、Electron 三层 |
| 13 | Multi-Provider Adapter | meisijiya(provider-adapter) | dg-ai-notes(M04) | meisijiya 给 DeepSeek/Anthropic/OpenAI 归一,dg-ai-notes 给 30+ provider 的协议层 |
| 14 | Event-Driven Bus | dg-ai-notes(M07) | shareAI-lab(s04 hooks) | dg-ai-notes 独有:subscribe(旁观) vs on(决策)两条管道 + fail-closed 设计;SDK 视角事件枚举(v0.83.0 增量: agent_settled, thinking_level_select)见 dg-piagent/references/sdk_doc/04-events.md |

## 三个资源的互补之处(读哪个学哪个)

| 你想解决的问题 | 推荐读 |
|---|---|
| 想理解"Agent 是什么,什么不是" | shareAI-lab README §"Where Agency Comes From" |
| 想从 0 用 30 行写一个 Agent | shareAI-lab s01-s02 |
| 想给 Loop 加权限和扩展点 | shareAI-lab s03-s04 |
| 想做桌面/服务端产品 | meisijiya s05-s09 |
| 想做六层架构的责任划分 | meisijiya README §"六层架构" |
| 想做 Memory 三层所有权 | meisijiya s10-s12 |
| 想做多 Provider 接入 | meisijiya docs/appendix/provider-adapter.md |
| 想做审计 + 防篡改 | meisijiya s23 |
| 想做生产级 SDK 二次开发 | dg-ai-notes M01-M10 |
| 想做 Agent Loop 的工程化分层 | dg-ai-notes M03(内核+叠加) |
| 想做事件监听的两条管道 | dg-ai-notes M07 |
| 想做工具系统的 5 步管道 | dg-ai-notes M05 |
| 想把 Agent 做成服务 | dg-ai-notes P07 |

## 引用约定

- 所有三个上游均为 MIT 或宽松许可(已查证)
- 本 skill 的所有内容均为**重新表述**,不复制任何上游逐字原文
- 引用方式:每篇 references 文件末尾以"引用与致谢"段落标源,正文最长引用 ≤ 1 句短引 + 立即标源
- 上游 commit 锚点:`shareAI-lab/learn-claude-code` commit `f9e8b280`(调研时锁定)

## 边界声明

- **本 skill 不替代上游教程**——三个资源都值得精读,本 skill 是设计视角的提炼,不是教学视角的替代
- **本 skill 不涵盖模型训练**——Harness 视角,Agency 来自模型训练但训练本身超出范围
- **本 skill 不涵盖纯 prompt engineering**——只要 harness 决策相关的 prompt 组装,才在本 skill 范围内
- **本 skill 不替代 ADR**——跨团队 / breaking decision 应该写 ADR,本 skill 是教学记录不是 ADR

---

## Federation — vendor-neutral vs vendor-pinned

本 skill 不替代 vendor-pinned 的 SDK 助手。新读者若要用 pi-coding-agent 直接干活
(典型路径:`createAgentSession` / `defineTool` / `pi.on` / `session.subscribe` / SSE streaming),
请去 install 上游 `dg-piagent`——指针在 `docs/awesome-skills.md`。本 skill 维持 vendor-neutral
的设计提炼视角;`dg-piagent` 提供 SDK-versioned 的 API 精度,两边各管一段。

**Federation contract**: 上游 `dg-piagent` 是 SDK 助手(vendor-pinned,SDK 版本变化时随之演进);
本 skill 是元技能(vendor-neutral,提炼设计哲学与机制对照)。读者带着"想用真 SDK 干活"的需求进来,
本 skill 把他们导出去自己 install 上游;读者带着"想理解为什么这么设计"的需求进来,本 skill 就是
归宿。两边都不试图做对方的事。

## 延伸阅读

**伦理 / 隐私视角,非工程必须,展开请读原文**。WanLanglin 仓库里有两份从 Claude Code 逆向出来的伦理 / 治理文档,跟本 skill 的工程视角互补但属于另一条脉络:

- **`docs/zh/grove-system.md`** — Grove 系统:多用户 / 多 Agent 共享环境下的权限分层与审计拓扑。聚焦"谁能在什么上下文里看到什么"。
- **`docs/zh/anti-distillation.md`** — Anti-Distillation:防止 Agent 的输出被用作训练数据蒸馏(尤其是企业私有知识)。聚焦"如何让模型输出不可被低成本复用"。

> 这两份不在本 skill 的工程主线里。引用本 skill 做 Harness 设计时不需要读它们;但当项目涉及**共享环境 / 数据治理 / 合规边界**时,这两份是起步读物。本 skill 保持工程中立,这两份保持伦理中立,两边不互相覆盖。

**使用方式**:本节给出的指针是"起步读物",不是"读完就够"。涉及伦理 / 合规问题的项目,需要把 WanLanglin 的两份文档读完后,再回看本 skill 的 04-production §轴 5(安全与权限),做对应的工程适配。两条脉络相互引用,不要只看一边。

## 致谢

- `shareAI-lab/learn-claude-code`——作者团队把 Claude Code 的工程化教学做到了极致的清晰
- `meisijiya/learn-workbuddy`——把桌面 Agent 的工程复杂度拆解成 24 个独立可学的机制
- `dg-ai-notes.pages.dev`——把 Pi Agent SDK 的源码拆成 17 个可独立阅读的章节,补足生产视角
- `walkinglabs/learn-harness-engineering`——把 Agent 工程抽象成 5 子系统 + Loop / Graph / Frontier 三视角,补充产品视角
- `WanLanglin/-awesome-cc-harness`——逆向 Claude Code 512K LOC 给出 ROI 量化证据与 12 维竞品对比,补充工程化深度