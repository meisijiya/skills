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
   - **一一映射声明**:`feature_list.json` 中**每一条 feature 对应唯一一个 spec**;ticket 不是 feature 的同义词,而是 spec 的**原子拆分**(tracer-bullet 切片)。不要把多个 feature 合并到同一个 spec,也不要把一个 feature 拆到多个 spec 里。
3. **拆 tickets**——必须紧跟 spec:
   - 调用 `to-tickets` 把 spec 拆成 tracer-bullet 垂直切片,带 blockers,发布到同一 tracker
4. **实现 + 评审**:按 ticket 的依赖序工作;每个 ticket 完成后调用 `code-review-and-quality` 走五轴评审,产出 P0/P1 修复清单
   - **git 提交节奏**(代码即文档,必须遵守):
     - **spec 定稿**单独一次提交(在 to-spec 后、开始实现前),commit message 含 `spec:` 与 feature 名 / spec id
     - **实现**按 ticket 提交,每个 ticket 至少一次 commit,commit message 含 `feat:` 与 ticket id
     - **bug 修复**单独一次提交(不与实现混),commit message 含 `fix:` 与 feature 名 / spec id
     - 这样 `git log --grep="<feature 名>"` 能串起 spec→实现→bugfix 三段历史
5. **凝练 feature.json 条目**:从 spec 与交付中提炼一条精炼的 feature 描述写回 `feature_list.json`(遵守 `harness-creator` 的字段约定),把该条标记 `passes: true`
6. **记录该 feature 的 bug 修复(`fix_bug_description`)**——**条件步骤**:
   - 仅当该 feature 在交付(`passes: true`)之后**确实产生过 bug 且已修复完成**时才写
   - 字段值必须包含:bug 现象(可复现的输入与实际输出)、根因定位(代码/数据/时序哪一层)、修复动作(改了什么文件/函数/Schema)、回归验证(跑了哪个测试/命令验证不再复现)
   - **未修复完成的 bug 不写**——避免出现「修复进行中」与「已修复」两种状态混淆
   - **同 feature 的 bug 后续复现** → 必须**重写或补缺**该 feature 的 `fix_bug_description`,把新现象、新根因、新修复动作并入;不允许只在末尾追加
   - 该字段引用的 bug 修复 commit 必须在 commit message 里关联 feature 名 / spec id(`fix(<feature>): ...`),确保能从 git log 反查


**交接物**(单 feature 完成后):

- issue tracker 上的 spec 与若干 ticket(其中至少一个被 `passes` 标记的 ticket 实现)
- `feature_list.json` 中至少新增一条 `passes: true` 的条目
- review 的 P0/P1 全部修复或明确接受

**停止条件**:`feature_list.json` 对应条目的 `passes: true`,无未结 P0 review,且该 feature 当前所有已知 bug 都已修复并写入了 `fix_bug_description`(未产生过 bug 则字段可缺失,但不得留半成品)。

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
- **`fix_bug_description` 是 feature 的长期补丁账本**:只写已修复完成的 bug;同一 feature 的 bug 复现必须重写或补缺该字段,而不是追加历史;不得把修复中的 bug 提前写入。
- **feature / spec / ticket / commit 一一映射**:`feature_list.json` 每条 feature 对应唯一 spec;spec 拆 ticket;ticket 提交实现;bug 提交修复。一条 feature 在 git 历史里应能通过 `git log --grep="<feature 名>"` 串起 spec→实现→bugfix 三段。


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
| 一个 `passes: true` 的 feature 复现了已修复过的 bug | 回到该 feature,重写/补缺 `fix_bug_description`,而不是追加 |
| git log 无法通过 feature 名串起 spec / 实现 / bugfix 三段 | 停下补 commit 关联(amend 或加 fixup),而不是继续往前推 |

## 黑名单(明确不要做)

以下动作视为 harness 失序,违反任一条立即停下并修正:

- **不要并行多个 feature**:一个会话只跑一个 feature 的阶段二循环;第二个 feature 必须等当前 feature `passes: true` 后,在下一轮阶段二再开始
- **不要把进度叙事写进 `AGENTS.md`**:AGENTS.md 是项目级契约,不是会话日志;进度写到 `progress.md`,下一棒从 `session-handoff.md` 接
- **不要把 ephemeral spec 写进仓库 git 历史**:spec 生命周期已结束后,只留精炼条目在 `feature_list.json`;`docs/specs/` 下的临时 spec 文件应在收尾阶段删除,不随 commit 长期保留
- **不要在 `feature_list.json` 写半成品 `passes`**:未跑完阶段二停止条件的 feature 一律 `passes: false`
- **不要把 `fix_bug_description` 写成历史叙事**:只写已修复的 bug;复现必须重写/补缺,不允许追加



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
- [ ] 该 feature 当前所有已知 bug 已修复,`fix_bug_description` 已更新(未产生过 bug 可跳过,但不得留半成品)
- [ ] `git log --grep="<feature 名>"` 能串起 spec / 实现 / bugfix 三段(代码即文档)
- [ ] 黑名单 5 项自检全过(无并行 feature / AGENTS.md 无进度叙事 / 无 ephemeral spec 残留 / 无半成品 passes / 无 fix_bug_description 追加)
- [ ] review 的 P0 已修复或被明确接受

**收尾**:

- [ ] `progress.md` 与 `session-handoff.md` 不携带过期叙事
- [ ] `feature_list.json` 当前条目与代码现状一致
- [ ] ephemeral spec 已退出默认上下文
- [ ] 下一棒只读三件状态文件即可开始工作
