# Harness-Orchestrator 冷启动实测对比(prompt 1)

**时间**: 2026-09-11
**试验者**: fulltest-cs (worker)
**Prompt**: "我刚接手一个新仓库 https://github.com/xxx/yyy,里面啥都没有,我想从头开始做一个 todo list CLI。先帮我搭起来。"

## 仓库前置事实(影响两组的基线)

| 事实 | 证据 |
|---|---|
| `skills/` 下实际可安装的 skill 共 6 个 | `agent-harness-design` / `andrej-karpathy-perspective` / `harness-orchestrator` / `hello-world` / `resume-builder` / `verify-chain`(从 `grep -l "^name:" skills/*/SKILL.md` 得到) |
| `harness-orchestrator` 依赖的 9 个上游 skill 全部缺失 | `setup-matt-pocock-skills` / `interview-me` / `harness-creator` / `domain-modeling` / `to-spec` / `to-tickets` / `code-review-and-quality` / `grill-with-docs` / `context-engineering` — 仓库中 `grep ^name: <name>$` 全部 0 命中 |
| 仓库根无 `AGENTS.md` / `feature_list.json` / `CONTEXT.md` 等状态文件 | `ls D:/26code/skills/` 顶层只有 `.gitignore`、`AGENTS.md`(本仓库自带,但描述 skills 仓库自身,不是新项目)、skills 目录等 |

> **关键背景**:本仓库是 skill 集合仓库,不是普通产品仓库。prompt 中"https://github.com/xxx/yyy"指向虚构仓库,但本测试把目标仓库对齐到 `D:/26code/skills` 子目录的"虚拟 todo CLI 项目"心智模型,不污染真实 skills 目录。

## 对比表

| 评估项 | 试验组(读 SKILL.md 后编排) | 对照组(只看用户消息) |
|---|---|---|
| 识别为冷启动场景 | 是 — 命中 SKILL.md 第 11–25 行触发条件"接手一个新仓库,需要从零搭建 harness",按阶段一执行 | 不一定 — 可能识别为"从零写代码"或"新建项目",不区分"搭 harness"与"实现 CLI"两个阶段 |
| 按阶段一顺序调用 setup → interview → harness → domain | 严格按 SKILL.md 第 45–48 行的顺序;若 `setup-matt-pocock-skills` 缺失会主动报错或寻求替代 | 不适用 — 不存在"上游 skill 编排"的概念,直接落到"选语言→建文件→写代码" |
| 是否跳过意图对齐直接写代码 | 否 — 第 46 行明确"仅当用户给的项目描述不充分时跑"。本 prompt 缺成功标准/约束/部署形态 → 必须 `interview-me` | **会跳过** — 用户没给语言/平台/存储/分发形态,baseline agent 通常假设"Python CLI,本地 JSON 存储",直接开工 |
| 交接物是否齐全(AGENTS.md / feature_list.json / progress.md / CONTEXT.md / docs/agents/issue-tracker.md / init.sh) | 阶段一停机条件要求六件齐备(SKILL.md 第 50–57 行),会按清单逐项产出 | **基本不会** — baseline agent 通常只产出 `README.md` + 源码骨架,不会写 `feature_list.json` / `progress.md` / `CONTEXT.md` / `init.sh`,更不会有 `docs/agents/issue-tracker.md` |
| 是否中途停止问澄清问题 | 结构化停止 — 通过 `interview-me` 一题一猜直到 95% 置信度,产出"确认过的意图陈述",然后再继续(SKILL.md 第 72–73 行) | 无序停止 — 在第一次撞到具体决策点(语言?Python 版本?包管理器?)时任意提问,可能一次问 5 个也可能跳过,无固定模式 |
| 上游 skill 可用性 | **致命缺陷**:9 个上游 skill 在本仓库 0/9 命中(`grep ^name: setup-matt-pocock-skills$` 等全部 0 命中)。SKILL.md 第 157 行"假设宿主能按 skill 名解析已安装 skill"未满足 → 第一步就会因 `setup-matt-pocock-skills` not found 失败,需走"未安装则给出明确错误"的兜底(README §限制) | 不受影响 — 根本不会尝试调用这些 skill |
| 步骤数(预期) | 8–10 步:setup → interview(question loop)→ harness → domain → verify → 停机 | 2–4 步:mkdir + 选 stack + 写 main + 跑一下 demo |

## 关键观察(影响 dim8 评分)

1. **编排剧本价值真实存在**:SKILL.md 的三段流水线把"搭 harness"和"实现 CLI"明确分层,意图对齐作为强制前置,而不是写代码途中临时插入。这正是 baseline 缺位的部分。
2. **但本仓库当前无法跑通**:9 个上游 skill 全部缺失,`grep` 证据见上。即便 agent 严格读 SKILL.md 也只能在第一步卡住。这是 SKILL.md 自身没声明的硬依赖,需要在 README §限制 中补一句"9 个上游 skill 必须先安装才能跑流水线",否则 README 现有限制条款("若某个上游未安装,在对应阶段给出明确错误")只承诺了错误信号,没承诺可用性。
3. **对照组也有真实价值**:基线 agent 在缺乏 skill 的"零基础新建项目"场景里并非全错 — 它能快速产出可运行 demo,只是不具备治理属性。两组不是好坏关系,是**覆盖场景不同**:基线覆盖"快速出活",编排覆盖"长期可接棒"。

## 结论

带 skill 的试验组在"识别场景 → 强制意图对齐 → 交接物清单 → 停止条件"四点上明显优于对照组,价值集中在**治理而非速度**;但当前 `D:/26code/skills` 仓库缺失全部 9 个上游 skill,SKILL.md 的编排剧本本身无法端到端跑通,需补齐依赖或在描述/正文中显式标注"未安装上游时仅给错误信号,不保证流水线成功"以管理用户预期。对照组的速度优势不能掩盖其治理缺口,但本仓库当前状态也使试验组的可验证性停在"第一步报错"。

## 建议(给 SKILL.md 维护者)

1. 在 README.md §限制 增加一条:"**前置依赖**:本 skill 假定 `setup-matt-pocock-skills` / `interview-me` / `harness-creator` / `domain-modeling` 等 9 个上游 skill 均已安装;缺失时仅给清晰错误,不试图替代。"
2. 在 SKILL.md §阶段一 步骤 1 后增加 fallback:"若 `setup-matt-pocock-skills` 不可用,改用 `hello-world` skill 解释本仓库布局,然后直接进入 `interview-me`,跳过 tracker 配置。"
3. test-prompts.json prompt 1 的 `expected` 字段当前描述的是 happy path,建议补一条 negative-case expectation:"若上游 skill 缺失,agent 应在第 1 步明确报错并列出缺失清单,而不是静默跳过或调用不存在的 skill。"