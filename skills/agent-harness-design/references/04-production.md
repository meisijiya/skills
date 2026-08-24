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

> **技巧**:每个事件落库时打上 `session_id` + `turn_id` 双标签,做 funnel 分析时不用回溯 transcript。**优先落盘事件而非 state**——状态是事件流的派生,直接落状态会导致后续难以回放。

**告警分层**:429 / Provider 5xx 是 warning;连续 3 次 retry 失败转 critical;audit 哈希链断链 → page on-call。告警太多 = 没告警;分层后 on-call 才能在半夜醒来的第一秒分轻重。
| 整轮结束 | **`agent_settled`(每 prompt 只发一次,可靠信号)** |
| 落库技巧 | 首选 `subscribe`(不被 await);订阅不到的 5 个决策点走 `on` + fire-and-forget |

**验收**:
- `grep agent_settled` 日志,确认每个 prompt 一次
- `grep tool_execution_start | wc -l` 与 `grep tool_execution_end | wc -l` 相等
- Provider 429 时告警能触发

### 上下文四级压缩管道(WanLanglin §8 / §3.3)

Agent 产品跑起来后,token 增长是最常见的真实瓶颈——即使 1M context window 在长对话里也会被填满。WanLanglin §8 §3.3 给出**四级压缩管道**,从轻到重逐级触发,Claude Code 的实现就是这四级:

| # | 层级 | 名字 | 成本 / 延迟 | 触发时机 | 做什么 |
|---|---|---|---|---|---|
| 1 | 极轻 | **Snip**(历史截断) | 极低 / ~0ms | 每轮 | Feature-gated 历史截断;释放少量 token;几乎无延迟 |
| 2 | 轻 | **Microcompact**(老化工具结果缩减) | 低 / ~1ms | 每轮 | 把 3 轮前的工具结果替换为 `[Previous: used {tool}]` 占位符;缓存压缩结果 |
| 3 | 中 | **Context-Collapse**(读时投射) | 中 / ~5ms | 每轮 | 不修改消息数组,只在读取时按粒度排空可折叠上下文;低成本、渐进、可逆 |
| 4 | 重 | **Autocompact**(LLM 全对话摘要) | 高 / ~2s | `> 50k tokens` 时才触发 | 保存完整 transcript 到磁盘,LLM 总结所有消息,用摘要替换;最重量级,释放最多空间 |

**执行顺序**:`snip → micro → context-collapse → auto`。各级互不排斥,可组合运行。**Autocompact 是最后一道**,只在仍然超阈值时才触发——前三道全跑完都不够才动用。

> **为什么不一次到位**:每一级都付出成本(延迟 / LLM 调用 / 信息损失),按"信息损失和成本"从低到高排序,先尝试最轻的层级,只到必要时才动用全对话摘要。**约束执行顺序**:源码注释道 Snip 必须先于 Microcompact 跑(`Apply snip before microcompact`),Snip 释放的 token 数必须传给 Autocompact 的阈值检查。

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
# 2. 离线 demo + 资产完整性
python3 scripts/verify.py
```

`scripts/verify.py`(以 learn-workbuddy 为例)覆盖:
- Python 语法 + pytest(mini harness / REST/ACP / smoke / 资产)
- 24 章 `--demo` 离线入口
- 关键章节 `--interactive` 进退
- mini HTTP server smoke
- README 架构图 + SVG 引用 + clean-room 扫描

---

## 引用与致谢

本检查清单综合 `dg-ai-notes.pages.dev` P07 准备上线、`shareAI-lab/learn-claude-code` s15 集成 harness、`meisijiya/learn-workbuddy` docs/security-boundaries.md;`WanLanglin/-awesome-cc-harness` §8 §3.3 四级压缩管道(Snip / Microcompact / Context-Collapse / Autocompact)。