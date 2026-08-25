# 03 · Anti-patterns — 不要做什么

> 设计完成 / 加新机制后,跑这张自检表。每个反模式:"❌ 错" → "✅ 对" → "💥 为什么错"。

## 一、范式层(架构)

### A1 · 把 LLM API + if-else + 节点图当 Agent 做

- ❌ **错**:Drag-and-drop AI Agent builder、Prompt-chain 编排库,把 LLM 调用串成瀑布
- ✅ **对**:要么训练模型,要么构建 Harness——只有这两件事
- 💥 **为什么错**:不产生 Agency,只产生复杂度。模型已经在训练时学会了怎么做 Agent,你堆胶水代码等于强行覆盖它的判断

### A2 · 把权限检查、日志、通知硬编码进 while 循环

- ❌ **错**:`while True` 里加 `if dangerous: deny`、`if executed: log`、每轮末尾 `if user_input: notify`
- ✅ **对**:用 hooks 挂在循环外,循环本身一行不改
- 💥 **为什么错**:循环膨胀到不可维护,加任何新功能都要回到循环体改

### A3 · 把所有文档塞进 system prompt

- ❌ **错**:100 个工具的全 schema + 全部 Skills 全文 + 全部 memory 一次性塞进 prompt
- ✅ **对**:Skills catalog(name + description)进 prompt;全文按需 `load_skill` 调用
- 💥 **为什么错**:启动 prompt 几 MB,模型还没干活 OOM

### A4 · 让 Bash 首 token 决定权限

- ❌ **错**:`if command.startswith("rm"): deny`、`if "install" in command: confirm`
- ✅ **对**:走 WorkspaceScope 文件工具,Bash 命令被工具层拦截
- 💥 **为什么错**:`cat /etc/passwd` 首词是 cat;`echo rm` 是 echo 不是 rm

### A5 · 让高 score 覆盖高 authority

- ❌ **错**:记忆召回按相似度排第一,直接覆盖用户当前指令
- ✅ **对**:`current_turn > workspace_override > user_default` 三层 authority
- 💥 **为什么错**:检索相关性 ≠ 用户指令优先级

### A6 · 上下文只塞 system prompt

- ❌ **错**:把所有 Skills 全文 + 全部 memory + 长文档一次性塞进 system message,prompt 直接破 MB
- ✅ **对**:Skills catalog(name + description 一行 metadata)进 prompt;Skills 全文用 `load_skill` 懒加载;Memory 按 scope 召回 top-k
- 💥 **为什么错**:模型还没开始干活 OOM;长 prompt 注意力稀释,关键指令被冲淡(walkinglabs L04 §Context Engineering)

## 二、Loop 层(运行时)

### L1 · 让模型自报"任务完成"

- ❌ **错**:模型返回 "task is complete",Loop 就退
- ✅ **对**:独立评估器(可以是更便宜的模型)判断 goal 是否真满足,否则注入 reason 自动续跑
- 💥 **为什么错**:模型可能幻觉"完成"或"测试通过"

### L2 · 信任 provider `stop_reason` 是循环退出信号

- ❌ **错**:看到 `stop_reason: "end_turn"` 就 return
- ✅ **对**:实际驱动条件是 `toolCalls.length > 0 && !terminate`
- 💥 **为什么错**:流式响应里内容块与终止元数据可能不同事件到达

### L3 · 让异常 throw 打断循环

- ❌ **错**:工具抛 `RuntimeError`,循环体里没 catch,整个 session 崩
- ✅ **对**:异常翻译成 `ToolResultMessage { isError: true, content: "具体错误" }`
- 💥 **为什么错**:异常打断循环 = 整个 session 终止,用户体验崩坏

### L4 · 工具错误描述写"Read failed" / "查询失败"

- ❌ **错**:catch 异常后回 `isError: "Read failed"`
- ✅ **对**:"Offset 200 is beyond end of file (100 lines total)"、"表不存在,库里只有:sales, products, users"
- 💥 **为什么错**:具体描述才能让模型自我纠错;模糊描述 = 模型盲目重试

### L5 · 工具直接调 `fs.readFileSync` / `mysql2.query`

- ❌ **错**:工具实现里直接用系统 API
- ✅ **对**:通过最小化的 Operations 接口(ReadOperations / WriteOperations / BashOperations)
- 💥 **为什么错**:无法 Mock、无法远程执行、无法换容器环境

### L6 · 让同一个模型做 maker 和 checker

- ❌ **错**:同一个 LLM 既写代码又评审代码,或既生成又裁决("自评自")
- ✅ **对**:Generator 与 Evaluator 分离——用更便宜的模型做 verifier,或用确定性的工具(Linter / type checker / test runner)做裁决
- 💥 **为什么错**:模型对自己刚产出的输出有 confirmation bias;没有独立信号源,质量门形同虚设(walkinglabs L13 §Generator/Evaluator Separation)

### L7 · Loop 上没有外部状态

- ❌ **错**:Loop 纯在内存里跑,关掉 session 一切证据消失;模型说"做完了"你也无从查证
- ✅ **对**:JSONL append-only transcript + SHA256 哈希链 + head anchor;事件全部落盘
- 💥 **为什么错**:Verification Debt 累积——模型做错的成本全由用户承担,你没能力 replay;silent failure 不可见(walkinglabs L13 §Four Silent Costs 之 Verification Debt)

### L8 · 多个 Loop 各自追自己的目标

- ❌ **错**:两个 Loop(例如 Lead 与 Teammate)各自定义"完成",跑完各自声称 done,实际总目标未达
- ✅ **对**:Shared goal + 独立 `goal_gate` 评估器,跨 Loop 的目标必须在外部黑板上同步,任一 Loop 的"完成"由总评估器裁决
- 💥 **为什么错**:Goodhart / Conflict / Blindness Upward 三种结构性失败中的 Conflict——多目标冲突无人仲裁(walkinglabs L14 §Three Structural Failures)

## 三、上下文层(管理)

### C1 · context 满了就全量摘要

- ❌ **错**:token 超阈值 → 调 LLM 摘要整个 history
- ✅ **对**:四步管道 L1→L4,前三步零模型调用
- 💥 **为什么错**:摘要贵(1 次 API 调用)且丢信息;工具结果可重读,优先压缩

### C2 · 切压缩切点拆开 tool_use ↔ tool_result 配对

- ❌ **错**:为了"省空间"把 `tool_use` 切到一边,`tool_result` 切到另一边
- ✅ **对**:切点只能是 user / assistant;tool_result 必须紧跟其 ToolCall
- 💥 **为什么错**:配对错乱 = 模型看不到自己请求的结果,无法继续推理

### C3 · 把 transcript 复制成 memory

- ❌ **错**:session 结束前把整个 transcript 写入 user memory
- ✅ **对**:`select_memory_candidate()` 显式筛选 + scope 判定 + `should_store_memory()` 去重
- 💥 **为什么错**:transcript 是 session 证据,memory 是跨 session 蒸馏;两者性质不同

### C4 · 压缩时改 durable state

- ❌ **错**:压缩摘要里"修正"了之前的事实
- ✅ **对**:`DurableContextState` 旁路压缩;`frozen=True` 强制不可改写
- 💥 **为什么错**:模型摘要可能改写事实,导致 silent failure

### C5 · 让 DENY 被 approval 覆盖

- ❌ **错**:`DENY` 也走 `Approver.ask_user()`,用户能取消禁止
- ✅ **对**:`ALLOW/DENY` 路径**不**调用 Approver;只 `ASK` 状态弹窗
- 💥 **为什么错**:暗示用户有权覆盖系统边界——安全架构崩塌

## 四、多 Agent 层(协作)

### M1 · 子 Agent 的所有 tool_call 都返回主窗口

- ❌ **错**:主 Agent 看到子 Agent 的每一步工具调用和中间结果
- ✅ **对**:子 Agent 独立 `messages[]`,只回最终文本
- 💥 **为什么错**:主窗口上下文秒爆,失去隔离意义

### M2 · 让模型 remove worktree

- ❌ **错**:`remove_worktree` 是个普通工具,模型能调
- ✅ **对**:cleanup 是 host helper,模型看不见,只 host 能调
- 💥 **为什么错**:任务所有权、租约、Git 状态需先查清,模型无能力保证

### M3 · 团队 Agent 互相发送无限消息

- ❌ **错**:Lead ↔ Teammate 一来一回发消息
- ✅ **对**:Team 通信走共享黑板(TaskList / Plan / 状态摘要),消息有类型化协议
- 💥 **为什么错**:消息爆炸 = 上下文失控;黑板天然可重放

### M4 · 同文件并行编辑不串行化

- ❌ **错**:两个并行 edit_file 改同一个文件,谁先谁后随机
- ✅ **对**:Edit 内部 `withFileMutationQueue` 对同文件串行化
- 💥 **为什么错**:写丢失 / 文件 corruption

## 五、运营层(产品化)

### P1 · 总预算不足就删除安全规则

- ❌ **错**:prompt 拼装时空间不够,把 permission 规则删了
- ✅ **对**:`PromptBudgetError` 阻止 provider 调用,required 必须 fail-closed
- 💥 **为什么错**:用户安全 > prompt 完整

### P2 · 用 message_end 当整轮收尾

- ❌ **错**:看到 `message_end` 事件就落库、推 done
- ✅ **对**:用 `agent_settled`(每 prompt 只发一次,可靠结束信号)
- 💥 **为什么错**:多轮 ReAct 会触发多次 `message_end`,重复落库

### P3 · subscribe 里 await 阻塞主流程

- ❌ **错**:`session.subscribe` 监听器里 `await db.insert()`
- ✅ **对**:`subscribe` 监听器不被 await;必须 fire-and-forget
- 💥 **为什么错**:subscribe 不被 await,但你的 await 会拖慢主流程;改用 on + fire-and-forget

### P4 · 在 on handler 里 await 慢接口

- ❌ **错**:`on('tool_call', ...)` 里 `await db.query()`(查权限)
- ✅ **对**:把检查结果缓存到内存,handler 直接读;或用 `before_agent_start` 阶段批处理
- 💥 **为什么错**:on 是同步屏障,handler 慢 = 主流程慢

### P5 · 用 `~/.pi/agent/SYSTEM.md` 当全局人设

- 系统提示词注入入口(具体路径见上游 dg-piagent)

📦 **Federation**: For `pi-coding-agent` v0.83.0 API specifics (createAgentSession / defineTool / pi.on / session.subscribe / SSE streaming),
install the upstream `dg-piagent` skill — see pointer in `docs/awesome-skills.md`. Our skill stays vendor-neutral; `dg-piagent` stays SDK-versioned.

---

## 六、Graph 层 (多 Agent 图)

> 当 Agent 从单 Loop 升级为多 Agent 协作图,引入的不是"更多 Loop",而是**新的失败模式**。walkinglabs L14 把这一层单独切出来,因为图视角下的反模式跟 Loop 视角下不是同一类问题。

### G1 · 把 prompt 调优等同于 loop 调优

- ❌ **错**:模型答错就开始改 prompt,改 10 版还是同样的失败,没意识到是 loop 结构(goal / verify / feedback)错了
- ✅ **对**:先分诊——是模型不知道(改 prompt / 加 memory)?做不到(改工具)?不愿做(改反馈)?调不通(改 loop)?再选对应杠杆
- 💥 **为什么错**:把三层可调杠杆(prompt / tools / loop)当一层用,小杠杆撬大问题永远撬不动(walkinglabs L13 §The Six Primitives)

### G2 · 评审带宽不够还硬加并行

- ❌ **错**:为了"快"给同一任务开 5 个并行 Agent,每个都做完整推理,但你的注意力是串行的——评审只看得了 1 份
- ✅ **对**:先评估"我的评审带宽 = 多少份 / 单位时间",并行 Agent 数 ≤ 评审带宽;多余的并行只是把同一份错误复刻 5 份
- 💥 **为什么错**:Orchestration Tax——并行放大产出,但评审仍是串行资源;产出超出评审带宽的部分是负价值(walkinglabs L14 §Orchestration Tax)

---

## 自检流程

设计完成 / 加新机制后,按顺序跑:

1. 读完整张表,标红任何你用了的 ❌ 项
2. 对每个标红项,要么改成 ✅,要么在 commit message 里解释为什么这里特殊
3. 重跑本仓库 `scripts/verify.py`(自带最小自检,见 04-production.md §上线前两道门)+ 离线 mock 套件
4. 让另一只 agent 独立评审——它没参与设计,更容易发现反模式

---

## 引用与致谢

本反模式清单综合 `shareAI-lab/learn-claude-code` 的 anti-patterns 表、`meisijiya/learn-workbuddy` docs/security-boundaries.md 与 24 章误区、`dg-ai-notes.pages.dev` M05-M07 + P05-P07 中的工程陷阱;`walkinglabs/learn-harness-engineering` `lecture-04-...` §Context Engineering、`lecture-13-loop-engineering` §The Six Primitives + §Four Silent Costs、`lecture-14-graph-engineering` §Three Structural Failures + §Orchestration Tax。