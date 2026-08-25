# Harness Skeleton

最小可跑 Harness 骨架(30 行级),为 Workflow A "离线 mock" 与 Workflow C "回归测试"提供起步资产。

## 用法

```bash
cd skills/agent-harness-design/assets/harness-skeleton
python3 harness.py "What is 2+2?"          # 跑一次 mock agent
python3 test_harness.py                     # 跑 4 个断言自检
```

## 覆盖的 4 个最小机制

| 机制 | 文件位置 | 对应参考 |
|---|---|---|
| Agent Loop (while 循环) | `harness.py:run` | [`references/01-mindset.md` §两条事件管道](../../references/01-mindset.md) |
| Tool Dispatch (dict 查表) | `harness.py:TOOLS + call_tool` | [`references/02-checklist.md` §2 Tool Registry](../../references/02-checklist.md) |
| Permission (DENY 永不弹窗) | `harness.py:PERMISSION_DENY` | [`references/02-checklist.md` §4 Permission / Hooks](../../references/02-checklist.md) |
| Hooks (post-tool 监听) | `harness.py:hook_post_tool` | [`references/02-checklist.md` §14 Event-Driven Bus](../../references/02-checklist.md) |

## 升级路径

| 当前实现 | production 应改 |
|---|---|
| `TOOLS = {...}` 单 dict | schema + handler + policy 三层独立(`02-checklist §2 §3`) |
| `PERMISSION_DENY` 单层集合 | decide / resolve / run 三段式(`02-checklist §4`) |
| `hook_post_tool` 单监听 | subscribe / on 两条管道 + 5 决策点(`02-checklist §14`) |
| 固定 `max_turns=3` | Context Compact 四步管道 + Memory 三层(`02-checklist §5 §6`) |
| 无审计 | JSONL append-only + SHA256 + head anchor(`02-checklist §11`) |

## 为什么不是 framework

ponytail: 30 行 stdlib-only 起步足够让 fresh agent 跑通 "我的 Harness 启动成功" 的最小闭环。装框架(autogen / crewai / langgraph)前先用这个骨架理解每个机制的内核,装框架后才会知道框架替你做了什么、藏了哪些反模式(`references/03-antipatterns.md` 的 30 项大部分来自"框架替你做了你没看懂的事")。