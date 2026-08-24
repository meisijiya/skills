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

### 5 层性能测量

Agent 产品跑起来后,性能问题往往不在"模型变慢了",而在**渲染/调度/网络/IO**某一层阻塞。光看 token/sec 看不到真瓶颈。WanLanglin §6.6 给出 5 层测量堆叠,从细到粗逐层定位:

| # | 测量层 | 工具 | 看什么 |
|---|---|---|---|
| 1 | **Headless Latency Profiler** | `headless_inspector` / eBPF tracing | 单次工具调用的真实耗时分解(模型 vs 网络 vs IO) |
| 2 | **Frame Timing** | `performance.measure()` / Chrome DevTools | TUI / Web UI 的渲染帧率,主线程是否被工具回调阻塞 |
| 3 | **FPS Tracker** | 自研 ring buffer / `requestAnimationFrame` | 持续滚动输出时帧率,目标是稳定 ≥ 30 fps |
| 4 | **Perfetto** | Perfetto trace viewer | 多流(messages + tool_result + UI events)按时间线对齐,可对比两个 session |
| 5 | **OpenTelemetry** | OTel SDK + Prometheus / Jaeger | 生产环境的跨服务追踪 + token 用量 + 错误率 |

> **逐层降级**:模型慢了先看 #1(是不是 transport / serialization 阻塞);UI 卡了先看 #2(是不是消息回填阻塞了主线程);全链路慢先看 #5(trace 看哪个 span 最长)。不要一开始就上 #5——粒度太粗,定位不到根因。

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

引用与致谢:本检查清单综合 `dg-ai-notes.pages.dev` P07 准备上线、`shareAI-lab/learn-claude-code` s15 集成 harness、`meisijiya/learn-workbuddy` docs/security-boundaries.md;`WanLanglin/-awesome-cc-harness` §6.6 五层性能测量。