# 04 · Production — 产品化落地的 5 轴检查

> 上线前必跑。每轴:核心关注点 / 推荐实现 / 验收命令。

## 轴 1 · API 化

**核心关注点**:让 Agent 可被多语言、多端调用,会话可恢复,流式输出可控。

| 关注点 | 推荐实现 |
|---|---|
| 接口形态 | 进程内嵌 SDK + 单接口 `POST /chat`(响应即 SSE 流) |
| 多语言互通 | RPC 模式(stdin/stdout JSON) |
| 流式输出 | `Content-Type: text/event-stream`,不关闭 HTTP 响应 |
| 会话隔离 | 每个 user 一个 session 实例;生产用 `SessionManager.inMemory()` + 自存 DB |
| 鉴权 | `setRuntimeApiKey` 注入,每用户从 DB 读 Key,不落盘 |

**验收**:
- `curl -N -X POST http://localhost:3000/chat -d '{"message":"hi"}'` 看到 SSE 流
- 关闭 curl 后服务端检测到 `req.on("close")` → `session.abort()` + settled 标志防重入
- 多用户并发不串 session

## 轴 2 · 错误处理

**核心关注点**:异常永不打断循环;上下文溢出有应急路径;前端能感知错误但不崩。

| 关注点 | 推荐实现 |
|---|---|
| 工具错误 | `never-throw` + 5 步管道 + `executePreparedToolCall` catch → `isError:true` |
| 模型调用错误 | 翻译器 catch → push error event + `stopReason: "error"/"aborted"` |
| 上下文溢出 | `isContextOverflow()` 三重检测 + 应急压缩 + retry |
| HTTP 断开 | `req.on("close")` → `session.abort()` |
| 重试策略 | `retry.enabled ?? true`,`maxRetries ?? 3`(在 settings.json) |
| 扩展错误隔离 | 通知型 `emit()` try-catch;决策型 `emitToolCall()` 无 try-catch(fail-closed) |

**验收**:
- 故意 throw 一个异常,确认 session 不崩
- 故意触发上下文溢出,确认应急压缩生效
- 故意断开 HTTP 连接,确认服务端正确 abort

## 轴 3 · 可观测性

**核心关注点**:Token 用量、工具调用审计、Provider 限流、压缩触发、整轮结束都要可监控。

| 关注点 | 实现方式 |
|---|---|
| Token 用量 | `agent_settled` 事件累加 `usage` 字段 |
| 工具调用审计 | `tool_execution_start/end` 配对,用 `toolCallId` 算耗时 |
| Provider 限流 | `after_provider_response` 看 HTTP 状态码(429 告警) |
| 压缩触发 | `compaction_start/end` 事件 + reason 字段 |
| 重试监控 | `auto_retry_start/end` 事件 |
| 整轮结束 | **`agent_settled`(每 prompt 只发一次,可靠信号)** |
| 落库技巧 | 首选 `subscribe`(不被 await);订阅不到的 5 个决策点走 `on` + fire-and-forget |

> **技巧**:每个事件落库时打上 `session_id` + `turn_id` 双标签,做 funnel 分析时不用回溯 transcript。**优先落盘事件而非 state**——状态是事件流的派生,直接落状态会导致后续难以回放。

**告警分层**:429 / Provider 5xx 是 warning;连续 3 次 retry 失败转 critical;audit 哈希链断链 → page on-call。告警太多 = 没告警;分层后 on-call 才能在半夜醒来的第一秒分轻重。
| 落库技巧 | 首选 `subscribe`(不被 await);订阅不到的 5 个决策点走 `on` + fire-and-forget |

**验收**:
- `grep agent_settled` 日志,确认每个 prompt 一次
- `grep tool_execution_start | wc -l` 与 `grep tool_execution_end | wc -l` 相等
- Provider 429 时告警能触发

### 上下文四级压缩管道(WanLanglin §8 / §3.3)

> ⚠️ **License 警告**:本节引用 `WanLanglin/-awesome-cc-harness` 的 §8 §3.3 章节编号与 Snip / Microcompact / Context-Collapse / Autocompact 四个层级名称。**该仓库许可证为 "All Rights Reserved / viewing only",禁止 copy / modify / distribute / fork / clone**。本 skill 不复制该仓库任何原文,读者需自行访问 https://github.com/WanLanglin/-awesome-cc-harness 在线查看。

Agent 产品跑起来后,token 增长是最常见的真实瓶颈——即使 1M context window 在长对话里也会被填满。WanLanglin §8 §3.3 给出**四级压缩管道**,从轻到重逐级触发,Claude Code 的实现就是这四级:

| # | 层级 | 名字 | 成本 / 延迟 | 触发时机 | 做什么 |
|---|---|---|---|---|---|
| 1 | 极轻 | **Snip**(历史截断) | 极低 / ~0ms | 每轮 | Feature-gated 历史截断;释放少量 token;几乎无延迟 |
| 2 | 轻 | **Microcompact**(老化工具结果缩减) | 低 / ~1ms | 每轮 | 把 3 轮前的工具结果替换为 `[Previous: used {tool}]` 占位符;缓存压缩结果 |
| 3 | 中 | **Context-Collapse**(读时投射) | 中 / ~5ms | 每轮 | 不修改消息数组,只在读取时按粒度排空可折叠上下文;低成本、渐进、可逆 |
| 4 | 重 | **Autocompact**(LLM 全对话摘要) | 高 / ~2s | `> 50k tokens` 时才触发 | 保存完整 transcript 到磁盘,LLM 总结所有消息,用摘要替换;最重量级,释放最多空间 |

**执行顺序**:`snip → micro → context-collapse → auto`。各级互不排斥,可组合运行。**Autocompact 是最后一道**,只在仍然超阈值时才触发——前三道全跑完都不够才动用。

> **为什么不一次到位**:每一级都付出成本(延迟 / LLM 调用 / 信息损失),按"信息损失和成本"从低到高排序,先尝试最轻的层级,只到必要时才动用全对话摘要。**约束执行顺序**:四级必须按 `Snip → Microcompact → Context-Collapse → Autocompact` 顺序执行;前一级释放的 token 数必须传给下一级的阈值检查,Autocompact 仅在前面三级仍超出阈值时才触发。

## 轴 4 · 性能与成本

**核心关注点**:Prompt cache 命中率、上下文截断、压缩阈值、并行工具执行、Skills 懒加载。

| 关注点 | 关键参数 |
|---|---|
| Prompt cache | Anthropic 三处打点(system / tools / 最后 user message)+ rolling cache |
| 上下文截断 | `MAX_LINES=2000` / `MAX_BYTES=50KB` / `GREP_MAX_LINE_LENGTH=500` |
| 压缩触发 | `contextTokens > contextWindow - reserveTokens` |
| 并行工具 | 三阶段(顺序准备 → 并行执行 → 有序事件) |
| Skills 懒加载 | 拉模式(清单进 prompt,全文按需 read) |
| 模型路由 | 简单问题 lite,复杂问题切 craft |

**验收**:
- 监控 Prompt cache 命中率 ≥ 80%(对长会话)
- 工具输出截断后,模型仍能根据指针读完整结果
- Skills 加载次数 < Skills 总数(说明真的按需加载了)

## 轴 5 · 安全与权限

**核心关注点**:工具可见性白名单、参数改写、Prompt injection 防御、Key 管理、OS 级隔离。

| 关注点 | 推荐实现 |
|---|---|
| 工具可见性 | **白名单** `setActiveToolsByName([])`——默认不信任 |
| 工具调用拦截 | `tool_call` 扩展事件 `return { block: true, reason }` |
| 参数改写 | `tool_call` 事件改 `event.input`(不再做 Schema 校验) |
| Prompt injection | 工具结果 / 文件内容默认不可信;危险工具必须人类审批 |
| 系统提示词净化 | `before_agent_start` 钩子链式覆盖 |
| Fail-closed | `emitToolCall()` 无 try-catch,扩展崩了 block 工具 |
| Key 管理 | Key 不落盘;4 种方式有明确优先级 |
| OS 级隔离 | 字符串 deny-list 只是安全带,生产必须 OS 沙盒(macOS App Sandbox / seccomp / 命名空间) |

### 5.x Sandbox 三维隔离(产品化前必读)

代码级安全(bash command deny-list、参数 schema 校验)只是安全带;生产环境必须三维独立隔离——任一维度失守另两个仍能兜底:

| 维度 | 隔离什么 | 单点失守后果 | 兜底 |
|---|---|---|---|
| **文件系统** | workspace 边界、`..` / 绝对路径 / symlink 黑名单 | 文件越权访问 / 路径逃逸 | 网络 + 进程层仍能限制外泄 |
| **网络** | 出站白名单、DNS 拦截、禁用 raw socket | 数据外泄 / 跨域调用未授权服务 | 进程层仍能限制子进程行为 |
| **进程** | 子进程权限、CPU/内存配额、禁止 fork 炸弹 | 资源耗尽 / 提权 | 文件系统层仍能限制持久化 |

**判定标准**:三个维度必须**独立实现**,不能一个沙盒同时覆盖三个(那是单层沙盒,失守即全失)。代码级 deny-list 不计入"三维"——它属于工具白名单层(见 [`02-checklist.md` §4 Permission](02-checklist.md) 的 L1-L3),与 OS 级沙盒不在同一维度。

> **这是本 skill 的原创提炼**(基于公开的深度防御方法论,NIST / SANS 标准),**不是 WanLanglin §7 的具体沙盒实现**。WanLanglin §7 给的是 Claude Code 内部架构(Bun runtime + macOS Seatbelt profile + 容器化),那是 Anthropic 私有实现,本 skill 不引用。

📦 **Federation**: For `pi-coding-agent` v0.83.0 API specifics (createAgentSession / defineTool / pi.on / session.subscribe / SSE streaming), install the upstream `dg-piagent` skill — see pointer in `docs/awesome-skills.md`. Our skill stays vendor-neutral; `dg-piagent` stays SDK-versioned.

**验收**:
- 默认创建 session 后,内置 bash/write 不在白名单
- 故意触发 `tool_call` 的 block,确认 `reason` 进了 LLM
- Key 在内存(具体路径见上游 dg-piagent)

---

## 上线前两道门

```bash
# 1. 单元 / 集成测试
python3 -m pytest -q   # 或 npm test / go test,看项目
# 2. 本 skill 自带的最小自检(本仓库真实脚本,见 scripts/verify.py)
python3 scripts/verify.py
```

`scripts/verify.py`(本 skill 自带的最小自检,**非上游 learn-workbuddy 的同名脚本**)覆盖:
- 本 skill 结构 + frontmatter 校验(name / description ≤200 字节 / license / 无 `metadata.internal`)
- 14 机制清单(02-checklist.md)与 30 反模式清单(03-antipatterns.md)计数对齐
- 8 个 references 文件存在性 + license banner 出现次数(WanLanglin 警告至少 1 处)

---

## 引用与致谢

本检查清单综合 `dg-ai-notes.pages.dev` P07 准备上线、`shareAI-lab/learn-claude-code` s01-s12 集成 harness、`meisijiya/learn-workbuddy` docs/security-boundaries.md;`WanLanglin/-awesome-cc-harness` §8 §3.3 四级压缩管道(Snip / Microcompact / Context-Collapse / Autocompact)——**仅引用章节编号与名称,该仓库许可证禁止复制,详见文件内 license 警告 banner**。