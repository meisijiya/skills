# 02 · Checklist — 14 个 Harness 机制清单

> 设计 / 评审 / 加新机制时,查这张表。每行:机制 / 为什么 / 在哪 / 如何验证。
>
> ⚠️ **License 摘要**:本文件引用的 5 个上游资源许可证分别为:`shareAI-lab/learn-claude-code` / `meisijiya/learn-workbuddy` / `walkinglabs/learn-harness-engineering` = **MIT**(可 re-derivation);`dg-ai-notes.pages.dev` 的 docs 子部分(含 dg-piagent/SKILL.md) = **CC-BY-SA-4.0**(只引用章节名称,本仓库不复制);`WanLanglin/-awesome-cc-harness` = **"All Rights Reserved / viewing only"**(禁止 copy / modify / distribute)。本文件 §1 7 Continue Sites 与 §2 工具分区算法 在自身框架内做了**重新表述**,**不复制** WanLanglin §3.2 / §3.4 原文段落、代码片段、量化数字、图表结构——读者需自行访问 https://github.com/WanLanglin/-awesome-cc-harness 在线查看。详见 `references/05-source-synthesis.md` §"License 摘要"。

## 总表

| # | 机制 | 为什么需要 | 在哪实现 | 验证方法 |
|---|---|---|---|---|
| 1 | **Agent Loop** | 一切的地基 | `agent_loop()` 函数 | 30 行能跑通 tool_use / tool_result |
| 2 | **Tool Registry / Dispatch** | 加工具不改循环 | `TOOL_HANDLERS[name]` dict | 加 1 个工具 = 加 1 行 schema + 1 行 handler |
| 3 | **Deferred Tool Loading** | 工具多了 prompt 爆炸 | `ToolSearch` + `DeferExecuteTool` 两步 | 加载 100 个工具,prompt 仍 < 1k tokens |
| 4 | **Permission / Hooks** | 自主 vs 安全的边界 | `decide` → `resolve` → `run` 三段 | DENY 不可被 ASK 覆盖;default.deny |
| 5 | **Context Compact** | 上下文总会满 | 四步管道 L1-L4 | 200k tokens 长会话不崩 |
| 6 | **Memory System** | 跨会话知识 | workspace / user / remote 三层 | 重启后召回正确事实 |
| 7 | **SubAgent / Team** | 单 Agent 顾不过来 | `fresh messages[]` + 邮箱 + 黑板 | 主 Agent 看不到子 Agent 推理细节 |
| 8 | **Task System** | 大目标拆小任务 | `.tasks/<id>.json` + `blockedBy` | 跨重启任务图完整恢复 |
| 9 | **MCP Connectors** | 外部能力接入 | `mcp__server__tool` 命名空间 | 工具池动态装配,host-side policy 生效 |
| 10 | **Skills System** | 知识按需加载 | `SKILL.md` 目录 + 全文按需 | 启动 prompt 只含 name+description |
| 11 | **Audit & Hash Chain** | 证据 + 防篡改 | JSONL append-only + SHA256 + head anchor | 任意条目篡改可检测;截断可检测 |
| 12 | **Session & Runtime** | 长期活着 | create / resume / close + Sidecar | 关闭 runtime 不删 transcript |
| 13 | **Multi-Provider Adapter** | Loop 稳定,provider 可换 | 协议 → 中性类型 → Loop | 换 provider Loop 一行不改 |
| 14 | **Event-Driven Bus** | 扩展点统一 | subscribe(只读) + on(决策) | 落库/审计走 subscribe;拦截走 on |

---

## 详细说明(每机制一行原则 + 关键约束 + 反模式链接)

### 1. Agent Loop

**原则**:循环最小化,只做四件事——调模型、检查 tool_use、执行工具、追加结果。

**关键约束**:
- `stopReason` 不是退出信号——"模型不输出 tool_use"才是
- 硬停止 fail-fast:`error` / `aborted` 不检查 followUp,直接 return
- 流式渲染:`context.messages[last]` 原地替换,UI 实时更新

**反模式**:把权限检查、日志、通知硬编码进循环体 → 用 hooks。

#### 7 Continue Sites

WanLanglin §3.2 逆向 Claude Code 后总结出 7 个"模型可能中断、需要 Harness 兜底续跑"的站点。每个 Continue Site 都有触发条件 + 恢复动作:

| # | Continue Site | 触发条件 | 恢复动作 |
|---|---|---|---|
| 1 | **Continue Site:上下文溢出** | `isContextOverflow()` 三重检测命中 | L1 截断 → L2 去重 → L3 修剪 → L4 摘要 → retry |
| 2 | **Continue Site:Provider 429 / 5xx** | HTTP 状态码命中限流或服务端错误 | `auto_retry` 配 backoff,`maxRetries ≥ 3`;超限转 hard error |
| 3 | **Continue Site:Tool 执行抛异常** | `execute()` 未被 catch | 转 `isError: true` 的 `ToolResultMessage`;不 throw 打断循环 |
| 4 | **Continue Site:Provider 流断开** | SSE / WebSocket 连接中断 | `req.on("close")` → `session.abort()` + settled 标志防重入 |
| 5 | **Continue Site:工具返回"不可恢复"** | 工具 schema 校验失败 / 致命资源缺失 | 注入错误事件 + 自动续跑一次;失败转 hard error |
| 6 | **Continue Site:规划目标未满足** | `goal_gate` 评估 goal 未达成 | 注入 reason 自动续跑;`maxContinuations` 防死循环 |
| 7 | **Continue Site:用户中途插队(steering)** | `steering` 队列非空 | 本轮结束后消费 steering,组装进下一轮 system prompt |

> **共性**:每个 Continue Site 都有**触发条件 → 恢复动作 → 兜底降级**三层。前两层失败时必须有 hard error,不能让 Loop 静默卡住。Loop 本身的 `while True` 不能包含任何 Site 的判断逻辑——Site 全部通过 dispatch map / hooks / on() 注入。

### 2. Tool Registry / Dispatch

**原则**:schema + handler + policy 三合一,单一真源。

**关键约束**:
- 未知工具 → 稳定 `ToolErrorCode`,不崩
- 参数错误 → 运行时 schema 校验(不止靠模型)
- 并发策略:任一工具 `executionMode: "sequential"` → 整批串行

**反模式**:用 if-elif 分发工具调用 → 用 dispatch map。

#### 工具分区算法(partitionToolCalls)

WanLanglin §3.4 逆向出的工具调度算法。模型一次返回 N 个 `tool_call`,Harness 需要把它们**切分到独立执行段**,每段内的工具并发,段间串行。

```text
partitionToolCalls(calls) → segments
  while calls not empty:
    group = []
    for call in calls (in order):
      if call.executionMode == "sequential":
        if group non-empty: emit group; reset group
        emit [call]   # 单独一段
      else:           # default: parallel-safe
        if call is read-only (no file mutation, no network write):
          group.append(call)
        else:          # write / destructive / sequential
          if group non-empty: emit group; reset group
          emit [call]
    emit group (last segment)
```

**关键原则**:

| 原则 | 含义 |
|---|---|
| **读并发,写串行** | 多个 read-only 工具可并行(同文件并发读安全);任意 write 必须独立段 |
| **sequential 工具独占段** | `executionMode: "sequential"` 标记的工具(典型:`git_commit`、`npm install`、状态机类)必须独占一段,不与其他工具并发 |
| **destructive 工具走 host helper** | `remove_worktree`、`drop_database` 这类不能暴露给模型 → 模型看不见,只能 host 调 |
| **context modifier 延迟应用** | 工具结果改 context 的工具(如 `load_skill`、`compress_context`)放在段尾应用,避免前置工具读到旧 context |

> **验证**:并发执行后,文件系统 / 数据库状态应该等价于任意串行顺序的结果。如果不,说明 partition 错了——读操作没真 read-only,或写操作没真独立。

### 3. Deferred Tool Loading

**原则**:工具先列目录,schema 用到再展开。

**关键约束**:
- 启动 prompt 只含 name + description(一行的 metadata)
- 调用 `load_skill(name)` 才返回全文
- session-scoped loaded cache,避免重复加载

**反模式**:把 100 个工具的全 schema 塞进 system prompt。

### 4. Permission / Hooks

**原则**:三段式(政策 → 解析 → 执行),三态(allow/ask/deny),fail-closed。

**关键约束**:
- DENY 路径**不**调用 Approver——不可被覆盖
- `default.deny`——未匹配 policy 的工具直接拒
- WorkspaceScope 防三类逃逸:`..` / 绝对路径 / symlink

**反模式**:用 Bash 首 token 决定权限(`cat /etc/passwd` 首词是 cat)。

### 5. Context Compact

**原则**:四步管道,信息损失和成本从低到高排。

**关键约束**:
- L1 工具结果截断 > L2 文件去重 > L3 历史修剪 > L4 摘要
- 前三步零模型调用,只有 L4 才花钱
- tool_use ↔ tool_result 配对保留,切点不能拆

**反模式**:context 满了就全量摘要(贵且丢信息)。

### 6. Memory System

**原则**:三层所有权分离 + 召回是只读派生视图。

**关键约束**:
- workspace(项目事实)/ user(偏好)/ remote(profile)所有权清晰
- 召回:scope → confidence → authority → dedupe → conflict → top-k → pack
- 当前会话指令优先级最高,不能被 memory 覆盖

**反模式**:把 transcript 复制成 memory。

### 7. SubAgent / Team

**原则**:上下文隔离 + 通信有边界。

**关键约束**:
- SubAgent:新 `messages[]`,只回最终文本,中间推理不污染主窗口
- Team:邮箱 + 黑板 + 类型化协议,持久队友可跨任务
- destructive 操作(remove_worktree)只能 host 调,模型看不见

**反模式**:子 Agent 的所有 tool_call 都返回主窗口 → 上下文爆炸。

### 8. Task System

**原则**:文件持久化任务图 + 原子认领。

**关键约束**:
- `.tasks/<id>.json`,每个 task 是独立文件
- `blockedBy` 边列表,两阶段构建(先 ID 再边)
- `claim_task()` 加锁,失败回滚,不静默回 `WORKDIR`

**反模式**:任务列表只在内存里,重启即丢。

### 9. MCP Connectors

**原则**:discovery → trust → call,主机拥有权限。

**关键约束**:
- 工具命名 `mcp__server__tool`,规范化防冲突
- 不信任 MCP server 自报的 `readOnlyHint` / `destructiveHint`
- host-side `MCP_HOST_POLICY` 显式 `(server, tool) → allow/confirm`
- 错误编码成 `tool_result` 错误,不终止循环

**反模式**:信任 MCP server 自报属性 → host 一定要 policy。

### 10. Skills System

**原则**:`SKILL.md` 目录 + 按需全文加载。

**关键约束**:
- frontmatter `name` + `description`(≤200 字符,触发条件必须显式)
- 启动 prompt 只含 metadata;正文按需 `load_skill` 调用
- description 必须说"做什么 + 何时用",否则 agent 不加载

**反模式**:description 只写"Git helper"——agent 永远不加载。

### 11. Audit & Hash Chain

**原则**:append-only 证据流 + 防篡改。

**关键约束**:
- SHA256 哈希链:`entry.hash = SHA256(data + prev_hash)`
- **额外 `audit.head` 锚点**(条数 + 链尾 hash)防删尾
- 安全分级:BLOCKED / DESTRUCTIVE / HIGH_RISK / CAUTION / SAFE

**反模式**:只算哈希链——任何合法前缀仍是合法链,删尾检测不到。

### 12. Session & Runtime

**原则**:逻辑会话可恢复,运行时必须重建。

**关键约束**:
- UI 不跑 agent——Electron main / renderer / preload 三层
- Sidecar JSON-RPC over Unix Socket
- 关闭 runtime 不删 transcript;resume 用 fresh adapter 重放
- 多领域 RPC 路由(session / tool / memory / mcp / skill / automation)

**反模式**:UI 直接调工具 → 权限边界崩塌。

### 13. Multi-Provider Adapter

**原则**:协议差异归一,Loop 只看中性类型。

**关键约束**:
- 中性类型:`ToolSpec(name, description, parameters)` / `ToolCall(id, name, arguments)` / `ModelTurn(text, tool_calls, raw_assistant)`
- 两层适配:章节路径(Anthropic-compatible)+ mini harness 路径(协议归一)
- 错误编码到流不抛异常
- Prompt cache:Anthropic 三处打点 + rolling cache

**反模式**:Loop 里硬编码 `tool_use_id` / `json.loads()` / Provider 特定字段。

### 14. Event-Driven Bus

**原则**:两条管道——subscribe(只读)vs on(可动手)。

**关键约束**:
- subscribe:不被 await,异步监听器自 catch,纯观察
- on:await 读返回值,5 个决策点独占(`input` / `before_agent_start` / `context` / `tool_call` / `tool_result`)
- fail-closed:`emitToolCall()` 无 try-catch,扩展崩了 block 工具

**反模式**:subscribe 里写 `tool_call` 处理 → 静默命中不了。

#### Hooks 决策点矩阵(按 Loop 生命周期)

> 这是本 skill 的**原创提炼**——按 Loop 生命周期切出 5 个决策点,不照搬任何具体产品的事件命名(Claude Code 有 26 个 hook 事件、Cursor / Copilot 各有命名体系,各家互不通用)。本表是通用框架,可映射到任意 Agent 系统。

| 决策点 | 类别 | 是否可动手 | 典型用途 | 失败模式 |
|---|---|---|---|---|
| `before_agent_start` | 配置 | ✅ 可改 system prompt | 注入 context / 改 system prompt | 改坏 prompt → 后续轮次降级 |
| `input` (UserPromptSubmit) | 验证 | ✅ 可 block | 参数校验 / 输入过滤 | 漏 block → 危险命令进入 Loop |
| `tool_call` | 拦截 | ✅ 可 block + 改 input | 权限拦截 / 参数改写 | await 慢接口 → 主流程拖慢 |
| `tool_result` | 审计 | ✅ 可改 result | 审计 / 脱敏 / 注入错误事件 | 改坏 result → 模型决策错误 |
| `agent_settled` | 通知 | ❌ 只读 | 整轮收尾 / 落库 / 指标上报 | 用 `message_end` 替代 → 多轮重复落库 |

**关键约束补充**:
- 决策型 emit 无 try-catch(fail-closed)——扩展崩了 block 工具,不静默吞错
- on handler 不 await 慢接口——把检查结果缓存到内存,handler 直接读,或挪到 `before_agent_start` 阶段批处理
- 落库首选 `subscribe`(不被 await + fire-and-forget);订阅不到的 5 个决策点用 `on` + fire-and-forget
- **不要在 `tool_call` handler 里 await DB 查询**——会让 Loop 主流程被拖慢;参考 [`03-antipatterns.md` P3 P4](03-antipatterns.md)

---

## 决策树:从 0 设计的实施顺序

```
1. Agent Loop + Tool Dispatch (s01, s02)
   ↓
2. Permission / Hooks (s04)
   ↓
3. Context Compact + Memory (s08, s09)
   ↓
4. SubAgent + Task System (s06, s10)
   ↓
5. Skills System + MCP (s07, s14)
   ↓
6. Multi-Provider Adapter (provider-adapter)
   ↓
7. Session & Runtime + Audit (s07-session, s09+s23)
   ↓
8. Team / Multi-Agent (s13)
   ↓
9. Event-Driven Bus (M07)
   ↓
10. Production Check (04-production.md)
```

每步独立可验证,跑离线 mock 后跑真实 key。

---

## 14 机制 × L1/L2/L3 适用度

不同 Harness 成熟度级别需要不同的机制组合。L1 项目不需要全套,L3 项目也不能跳过前面:

| # | 机制 | L1 Individual | L2 Small team | L3 Organization |
|---|---|---|---|---|
| 1 | Agent Loop | **必选** | **必选** | **必选** |
| 2 | Tool Registry / Dispatch | **必选** | **必选** | **必选** |
| 3 | Deferred Tool Loading | 可选 | **必选** | **必选** |
| 4 | Permission / Hooks | 可选 | **必选** | **必选** |
| 5 | Context Compact | 可选 | **必选** | **必选** |
| 6 | Memory System | 可选 | **必选** | **必选** |
| 7 | SubAgent / Team | 跳过 | 可选 | **必选** |
| 8 | Task System | 跳过 | 可选 | **必选** |
| 9 | MCP Connectors | 跳过 | 可选 | **必选** |
| 10 | Skills System | 可选 | 可选 | **必选** |
| 11 | Audit & Hash Chain | 跳过 | 可选 | **必选** |
| 12 | Session & Runtime | 跳过 | 可选 | **必选** |
| 13 | Multi-Provider Adapter | 跳过 | 可选 | **必选** |
| 14 | Event-Driven Bus | 跳过 | 跳过 | **必选** |

> **判断**:L1 个人项目先把 1 + 2 跑通(Loop + Tool Dispatch),其他都可省。L2 团队项目加 3-6(context / permission / memory)。L3 组织级项目基本要全套,顺序仍是 Loop → Tools → Permission → Context → Memory → SubAgent → 其他。**跳级必败**——L1 直接上 SubAgent 是经典错例。

---

## 引用与致谢

本清单综合 `shareAI-lab/learn-claude-code` 17 章机制、`meisijiya/learn-workbuddy` 24 章机制、`dg-ai-notes.pages.dev` Pi Agent M01-M10 + P01-P07;`WanLanglin/-awesome-cc-harness` §3.2 The Seven Continue Sites + §3.4 Tool Execution Orchestration。