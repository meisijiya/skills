"""harness.py 自检 — 跑通即视作 Loop + Dispatch + Permission + Hooks 4 机制落地。

无外部依赖(只用了 stdlib);ponytail: 1 个文件 + 1 个断言就够,无 framework。
"""

from harness import call_tool, run


def test_echo_returns_input():
    r = call_tool("echo", {"text": "hi"})
    assert r == {"echo": "hi"}, f"expected echo roundtrip, got {r}"


def test_denied_tool_returns_error():
    from harness import PERMISSION_DENY
    PERMISSION_DENY.add("echo")
    r = call_tool("echo", {"text": "x"})
    assert "denied" in r["error"], f"expected deny, got {r}"
    PERMISSION_DENY.discard("echo")  # cleanup


def test_unknown_tool_returns_error():
    r = call_tool("nope", {})
    assert "unknown" in r["error"]


def test_run_completes_n_turns():
    out = run("ping", max_turns=2)
    assert "completed 2 turns" in out


if __name__ == "__main__":
    for fn in [test_echo_returns_input, test_denied_tool_returns_error,
               test_unknown_tool_returns_error, test_run_completes_n_turns]:
        fn()
        print(f"PASS {fn.__name__}")
    print("all harness skeleton checks PASS")