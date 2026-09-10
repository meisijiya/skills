# harness-orchestrator

把"项目级 harness 上下文治理"拆成三段流水线的编排 skill:冷启动 → 单 feature → 收尾。

不实现任何子能力,只编排上游 skill 的调用顺序与交接物。

## 适用边界

| 适用 | 不适用 |
|---|---|
| 接手新仓库,从零搭建 harness | 一次性、范围明确的小任务(改一个变量名) |
| 开始一个新 feature,需要从意图一路推进到可验证交付 | CI / 自动批跑 / 非交互循环(本 skill 依赖对话式澄清) |
| 一个会话接近收尾,把 harness 状态文件剪枝到下一棒可接手 | 用户明确拒绝搭建 harness |
| harness 状态文件(AGENTS.md / feature_list.json / progress.md / session-handoff)失序 | 已知意图充分、范围清晰、不需要多会话治理的纯实现任务 |

**数据边界**:本 skill 只读写 harness 状态文件与领域词文件(`AGENTS.md`、`CONTEXT.md`、`feature_list.json`、`progress.md`、`session-handoff.md`、`docs/agents/*.md`、`docs/adr/*.md`),不读写业务源码、不读写凭据、不修改 issue tracker 之外的远程资源。

**权限**:通过上游 skill 间接操作 issue tracker 时,沿用上游 skill 的授权约定;本 skill 不另行获取新权限。


## 三段流水线

| 阶段 | 触发 | 关键产出 |
|---|---|---|
| 冷启动 | 新项目或 harness 缺失 | `docs/agents/issue-tracker.md`、`AGENTS.md`、`feature_list.json`、`progress.md`、`init.sh`、`CONTEXT.md` |
| 单 feature | `feature_list.json` 存在 `passes: false` 条目 | tracker 上的 spec + tickets、`feature_list.json` 新增 `passes: true` 条目 |
| 收尾 | 会话将结束或上下文 75% 满 | `progress.md` + `session-handoff.md` 只描述当前与下一棒 |

## 串起来的上游 skill

`setup-matt-pocock-skills`、`interview-me`、`grill-with-docs`、`harness-creator`、`domain-modeling`、`to-spec`、`to-tickets`、`code-review-and-quality`、`context-engineering`

## 安装

通过 npx skills 安装:

```bash
npx skills add <owner>/<repo> --skill harness-orchestrator
```

## 调用

Agent 在合适时机按 skill 名调用本 skill(参考 `grill-me` 的用法);不要把路径写在请求里。

## 跨阶段不变量

- spec 是 ephemeral 的:passes 后退出默认上下文
- `feature_list.json` 长存且精炼
- harness 状态文件不带历史叙事
- 可执行约束(测试/Schema/门禁)优先于文字说明
- 意图未对齐时不允许写 spec

## 限制

- 本 skill 不依赖特定 Agent 宿主;核心流程使用能力描述,不绑定品牌或私有命令
- 假设宿主能按 skill 名解析已安装 skill(同 `grill-me` 用法)
- 假设上游 9 个 skill 均可用;若某个上游未安装,在对应阶段给出明确错误并提示安装
