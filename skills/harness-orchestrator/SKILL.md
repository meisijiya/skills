---
name: harness-orchestrator
description: 编排 harness 上下文治理的三段流水线(冷启动→单 feature→收尾),串起 9 个上游 skill。触发词:启动新项目 / 搭建 harness / 新 feature / 项目收尾 / progress.md 过期 / session-handoff 续写。改名、typo、CI 批处理不要触发。
license: MIT
---

# Harness Orchestrator

把"项目级 harness 上下文治理"拆成三段流水线,每段告诉你**调哪个 skill、调之前要有什么、产出落在哪、何时停止**。本 skill 不实现任何子能力,只编排顺序。

## 何时使用

满足任一条时调用本 skill:

- 接手一个新仓库,需要从零搭建 harness
- 开始实现一个新 feature,需要从意图一路推进到可验证交付
- 一个会话接近收尾,需要把 harness 状态文件剪枝到下一棒可接手
- harness 状态文件(AGENTS.md / feature_list.json / progress.md / session-handoff)失序——过期、与代码矛盾、或携带冗长历史叙事

满足任一条时**不**调用本 skill:

- 任务是一次性、范围明确(改一个变量名、修一个 typo)
- 用户要求速度而非治理
- 在 CI / 自动批跑 / 非交互循环里——本 skill 依赖对话式澄清
- 当前仓库还没有 harness 状态文件,且用户**明确拒绝**搭建(尊重用户)

## 三段流水线

```
冷启动 ──→ 单 feature(可重复)──→ 收尾
   │              │                    │
   └──── 任何阶段发现意图不清 ──→ 回到 interview-me
```

---

## 阶段一:冷启动(每个项目只跑一次)

**目标**:让 harness 状态文件齐备且彼此对齐;让"问题域的语言"沉淀一次。

**触发**:仓库无 AGENTS.md 或 feature_list.json,或用户在 harness 失序时显式要求重建。

**步骤**(按顺序,缺一步则视为未完成):

1. 调用 `setup-matt-pocock-skills`,配置 issue tracker / triage 标签 / domain doc 布局。**必须最先跑**——后续 to-spec、to-tickets 都依赖它产出的 `docs/agents/issue-tracker.md`。
   - **若缺失**:按下方「上游 skill 缺失 / 调用失败的 fallback」表处理;不要用通用 setup 流程替代 `setup-matt-pocock-skills` 的 issue-tracker 配置。

2. 调用 `interview-me` 对齐用户的项目级意图(谁用、解决什么、成功的标准、约束)。**仅当用户给的项目描述不充分时跑**;若用户已给出明确一句话目标,可跳过。
3. 调用 `harness-creator` 创建 harness 状态文件:`AGENTS.md` / `feature_list.json` / `progress.md` / `init.sh`,按其"minimal harness first"原则,不擅自加 memory / 多 agent / 工具权限。
4. 调用 `domain-modeling` 沉淀首批领域词到 `CONTEXT.md`,**仅在领域词尚未存在时**;术语随设计立即写入,不要批量。

**交接物**(冷启动完成后必须存在):

- `docs/agents/issue-tracker.md`
- `AGENTS.md`
- `feature_list.json`
- `progress.md`
- `init.sh`(或等价的可运行验证命令清单)
- `CONTEXT.md`(若领域词存在)

**停止条件**:以上六项全部存在且彼此不矛盾——`AGENTS.md` 不与 `CONTEXT.md` 冲突,`feature_list.json` 的当前 feature 与 `progress.md` 的"下一步"一致。

---

## 阶段二:单 feature(每个 feature 跑一次,可循环)

**目标**:从一个尚待对齐的意图出发,落到可验证、可交接的 feature 交付。

**触发**:`feature_list.json` 中存在 `passes: false` 的条目,或用户给出新的需求描述。

**步骤**:

1. **对齐意图**——必须先做,不可跳过:
   - 调用 `interview-me`(默认路径),通过一题一猜把意图对齐到 95% 置信度,产出"确认过的意图陈述"
   - 若意图已经过对齐(用户已给出明确验收标准,或上一轮 `interview-me` 已确认),改用 `grill-with-docs` 反复打磨 spec 的同时沉淀 ADR 与领域词
2. **写 spec**——必须先做,不可跳过:
   - 调用 `to-spec` 把意图合成 spec 发布到 issue tracker;spec 必须用 `CONTEXT.md` 的术语,尊重 `docs/adr/` 既有决策
   - spec 仅服务本 feature,不在仓库内长期保留——这是**短期 spec**(ephemeral)
3. **拆 tickets**——必须紧跟 spec:
   - 调用 `to-tickets` 把 spec 拆成 tracer-bullet 垂直切片,带 blockers,发布到同一 tracker
4. **实现 + 评审**:按 ticket 的依赖序工作;每个 ticket 完成后调用 `code-review-and-quality` 走五轴评审,产出 P0/P1 修复清单
5. **凝练 feature.json 条目**:从 spec 与交付中提炼一条精炼的 feature 描述写回 `feature_list.json`(遵守 `harness-creator` 的字段约定),把该条标记 `passes: true`

**交接物**(单 feature 完成后):

- issue tracker 上的 spec 与若干 ticket(其中至少一个被 `passes` 标记的 ticket 实现)
- `feature_list.json` 中至少新增一条 `passes: true` 的条目
- review 的 P0/P1 全部修复或明确接受

**停止条件**:`feature_list.json` 对应条目的 `passes: true`,且无未结 P0 review。

---

## 阶段三:收尾(每个会话接近结束时跑一次)

**目标**:把 harness 状态文件剪枝到"下一棒可立刻接手",剔除过期与冗长历史叙事,保留精炼的事实。

**触发**:对话即将结束、上下文达到 75% 容量、或用户显式说"今天先到这里"。

**步骤**:

1. 调用 `context-engineering` 审视 5 层上下文,识别可裁剪项——过期 spec、已完成的失败尝试、长工具输出、对话往返。**按其"先压缩再丢弃"原则**保留结论、丢弃过程
2. 调用 `harness-creator` 的"audit"动作复核状态文件五子系统(Instructions / State / Verification / Scope / Lifecycle),记录最低分项
3. 调用 `domain-modeling` 收集本会话新沉淀的领域词与必要 ADR,立即更新 `CONTEXT.md` 与 `docs/adr/`
4. 重写 `progress.md` 与 `session-handoff.md`:
   - `progress.md` 只保留当前 feature 的"下一步具体动作",**不带历史叙事**
   - `session-handoff.md` 只保留交接下一棒的内容:**当前 feature / 阻塞 / 未结 P0 / 下一步第一动作**,不重复 feature_list.json 已有的事实
5. 删除临时 spec、临时 ticket、`.scratch/` 下的草稿——这些是 ephemeral,生命周期已结束

**交接物**(收尾完成后):

- `AGENTS.md` / `feature_list.json` / `progress.md` / `session-handoff.md` 四者不矛盾
- `CONTEXT.md` 与代码现状一致
- 没有携带超过两轮的过期叙事

**停止条件**:任一接班人在新会话中只读 `progress.md` + `session-handoff.md` + `feature_list.json` 三件即可开始工作,无需追问"上下文发生了什么"。

---

## 跨阶段不变量(贯穿三段,任何时候违反则视为 harness 失序)

- **spec 是 ephemeral 的**:spec 一旦 ticket 全部 `passes`,从仓库与 tracker 默认上下文中退出,只留精炼条目在 `feature_list.json`
- **`feature_list.json` 是长存的**:feature 描述必须精炼、可作为下一棒的入口,不带 spec 的展开内容
- **harness 状态文件不带历史叙事**:`AGENTS.md` / `progress.md` / `session-handoff.md` 只描述当前与下一棒,不重述已完成的旅程
- **可执行约束优先于文字说明**:凡是能写成测试、Schema、机器门禁的约束,必须写成可执行形式;文字要求只在无法机器化时使用
- **领域词随设计立即沉淀**:术语第一次被使用时就更新 `CONTEXT.md`,不要批量补
- **意图未对齐时不允许写 spec**:`interview-me` 的 95% 确认是 spec 的前置条件,不是后续审查项

---

## 反向触发(看到这些信号立刻停下,回到合适的 skill)

| 信号 | 应回到哪个 skill |
|---|---|
| 用户描述需求但缺"谁用、为什么、成功标准、约束"中任一项 | `interview-me` |
| spec 用词与 `CONTEXT.md` 已有术语冲突 | `domain-modeling` |
| harness 状态文件未生成或缺失 | 回到阶段一 |
| 代码与 spec 行为不一致 | `code-review-and-quality` 走五轴 |
| issue tracker 未配置 | `setup-matt-pocock-skills` |
| 收尾时发现状态文件携带过期内容 | `context-engineering` 剪枝 |
| 一个会话想跨多个 feature | 跑阶段二循环,不要合并多个 feature 进同一个会话 |

## 上游 skill 缺失 / 调用失败的 fallback(任一阶段通用)

任一上游 skill 缺失或调用失败时,**不要静默跳过、不要调用不存在的 skill**。按三段式处理:

| 触发条件 | 一线修复 | 仍失败兜底 |
|---|---|---|
| 单个上游 skill 报 `not found` / 未安装 | 在该阶段直接报错,列出缺失清单,提示用户 `npx skills add` 安装 | 该阶段标 `blocked`,后续阶段不前进,等用户装完再恢复 |
| 上游 skill 调用成功但**返回值不达停止条件**(例如 `interview-me` 未拿到 95% 确认) | 回到该 skill 重跑一次,把未达条件项作为输入 | 若连续 3 次仍不达标,停止该阶段并请用户决定是放宽验收还是人工对齐 |
| 上游 skill 调用过程中**静默失败**(无错误但产出空) | 立即停止流水线,把空产物与上游 skill 名一起写入 `progress.md` 的「阻塞」段 | 改用 `harness-creator` 的 audit 动作复核,若 audit 通过则跳过该空产物的阶段 |

**反例**:看到 `interview-me` 不可用就跳过意图对齐直接写 spec——这违反「意图未对齐时不允许写 spec」(跨阶段不变量),导致后续 spec 与用户实际意图脱钩。

## 中途 scope 漂移的反例(看到任一项立刻停下)

任一阶段开始后,如果出现以下信号,**停止当前阶段、回到 `interview-me` 重对齐**,而不是合并进当前会话:

- 用户在本阶段中途追加**新 feature 或新模块**(即使只有一句话)
- 用户在「下一步」前先要求**改当前 feature 的验收标准**
- 用户突然要求**切换技术栈 / 语言 / 框架**
- 用户要求**同时推进两个 feature**(「顺便把这个也做了」)

**反例**:在阶段二的 spec 撰写中途,用户说「再加个导出 CSV」——不能就地扩 spec,必须:1) 标记当前 spec 为 `paused`,2) 跑一次 `interview-me` 把导出 CSV 当成独立 feature 对齐,3) 在 `feature_list.json` 新增一条 `passes: false` 条目后,作为下一轮阶段二的入口。

---

## 与各上游 skill 的分工

| 上游 skill | 在流水线中负责 |
|---|---|
| `setup-matt-pocock-skills` | 仅阶段一,配置 issue tracker / triage / domain doc 布局 |
| `interview-me` | 阶段一与阶段二意图对齐 |
| `harness-creator` | 阶段一创建、阶段三 audit harness 状态文件 |
| `domain-modeling` | 阶段一沉淀首批词、阶段三更新词与 ADR |
| `to-spec` | 仅阶段二,把对齐后意图合成 spec |
| `to-tickets` | 仅阶段二,把 spec 拆成 tracer-bullet 垂直切片 |
| `grill-with-docs` | 阶段二的备选路径,意图已对齐时反复打磨 spec + 沉淀 ADR |
| `code-review-and-quality` | 仅阶段二,五轴评审每个 ticket |
| `context-engineering` | 仅阶段三,五层上下文审计与剪枝 |

本 skill 不复制上述 skill 的执行细节;在调用它们时直接传 skill 名,不要附带路径。

---

## 验证清单(每个阶段跑完后核对)

**冷启动**:

- [ ] `docs/agents/issue-tracker.md` 存在且记录了真实 tracker
- [ ] `AGENTS.md` / `feature_list.json` / `progress.md` / `init.sh` 四件齐备
- [ ] `CONTEXT.md` 含首批领域词
- [ ] 用户已对项目级意图给出明确 yes

**单 feature**:

- [ ] 用户已对该 feature 的意图陈述给出明确 yes(走 `interview-me` 或 `grill-with-docs`)
- [ ] issue tracker 上有 spec + 至少一个 ticket
- [ ] `feature_list.json` 有对应 `passes: true` 条目
- [ ] review 的 P0 已修复或被明确接受

**收尾**:

- [ ] `progress.md` 与 `session-handoff.md` 不携带过期叙事
- [ ] `feature_list.json` 当前条目与代码现状一致
- [ ] ephemeral spec 已退出默认上下文
- [ ] 下一棒只读三件状态文件即可开始工作
