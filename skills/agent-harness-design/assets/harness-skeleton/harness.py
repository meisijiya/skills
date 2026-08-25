"""最小可跑 Harness 骨架。

用法:
    python3 harness.py "What is 2+2?"

提供 Workflow A "离线 mock" 起步点——跑通即视作 "我的 Harness 启动成功"。

设计:30 行内实现 4 个最小机制 ——
  - Agent Loop (while 循环)
  - Tool Dispatch (dict 查表)
  - Permission (单层 DENY 永不弹窗)
  - Hooks (post-tool 监听)

不是生产代码,但跑通就能拿来对照 Workflow A 的 8 个设计步骤。
"""

from __future__ import annotations
import json
import sys

# ponytail: single tool, real harness 在 02-checklist §2 起步时把 dict 拆成 schema + handler + policy 三层

TOOLS = {
    "echo": lambda args: {"echo": args.get("text", "")},
}

PERMISSION_DENY = set()  # ponytail: 全局 deny list;三段式 (decide/resolve/run) 在 §4


def call_tool(name: str, args: dict) -> dict:
    if name in PERMISSION_DENY:
        return {"error": f"tool '{name}' denied by policy"}
    handler = TOOLS.get(name)
    if handler is None:
        return {"error": "unknown tool '" + name + "'"}
    return handler(args)


def hook_post_tool(name: str, result: dict) -> None:
    # ponytail: 当前只 audit-log;production 应改写 / 拦截 / 注入(见 02-checklist §14)
    print(f"[hook] {name} -> {json.dumps(result)}", file=sys.stderr)


def run(user_input: str, max_turns: int = 3) -> str:
    """最小 mock Agent Loop:每个 turn 调一次 echo,直到 max_turns。"""
    for turn in range(max_turns):
        result = call_tool("echo", {"text": f"turn {turn}: {user_input}"})
        hook_post_tool("echo", result)
    return f"completed {max_turns} turns"


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "hello"
    print(run(q))