#!/usr/bin/env python3
"""
agent-harness-design skill 自检脚本。

覆盖范围:
1. SKILL.md frontmatter 校验(name == 目录名 / description ≤200 字节 / license 字段 /
   无 metadata.internal / 无空 name)。
2. references/ 文件存在性校验(预期 8 个 .md)。
3. 14 机制清单计数(02-checklist.md 主表) == 14。
4. 30 反模式清单计数(03-antipatterns.md ### 标题) == 30。
5. WanLanglin license banner 出现次数 ≥ 1(确保 B4 修复有 trace)。
6. shareAI-lab 章节数声明修正检查(02-checklist 行文不应再出现 "17" + 中/日 这种旧声称)。

退出码:
- 0: 全部 PASS
- 1: 任意 FAIL
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
REFS_DIR = SKILL_DIR / "references"

EXPECTED_REFS = [
    "01-mindset.md",
    "02-checklist.md",
    "03-antipatterns.md",
    "04-production.md",
    "05-source-synthesis.md",
    "06-loop-engineering.md",
    "07-graph-engineering.md",
    "08-frontier-designs.md",
]

EXPECTED_DIR_NAME = SKILL_DIR.name
EXPECTED_MECHANISM_COUNT = 14
EXPECTED_ANTIPATTERN_COUNT = 30
DESCRIPTION_LINE_BYTE_LIMIT = 200  # AGENTS.md wc -c check


def fail(msg: str) -> None:
    print(f"  ❌ FAIL: {msg}")


def ok(msg: str) -> None:
    print(f"  ✅ PASS: {msg}")


def check_frontmatter() -> bool:
    print("\n[1] SKILL.md frontmatter 校验")
    passed = True
    if not SKILL_MD.exists():
        fail(f"SKILL.md 不存在: {SKILL_MD}")
        return False
    text = SKILL_MD.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        fail("frontmatter 不是文件首块(必须以 line 1 的 --- 开头,前无任何内容)")
        return False
    body_after_fm = text[m.end():]

    # 必须字段
    if "name:" not in m.group(1):
        fail("frontmatter 缺 name 字段")
        passed = False
    else:
        name_match = re.search(r"^name:\s*(\S+)\s*$", m.group(1), re.MULTILINE)
        if not name_match:
            fail("name 字段值无法解析")
            passed = False
        else:
            name = name_match.group(1)
            if name != EXPECTED_DIR_NAME:
                fail(f"name 字段 ({name}) 与目录名 ({EXPECTED_DIR_NAME}) 不一致")
                passed = False
            else:
                ok(f"name 字段 == 目录名 ({name})")

    if "description:" not in m.group(1):
        fail("frontmatter 缺 description 字段")
        passed = False
    else:
        # AGENTS.md 检查方式: 整行 (含 "description: " 前缀) wc -c ≤ 200 字节
        desc_line_match = re.search(r"^description:\s*(.+)$", m.group(1), re.MULTILINE)
        if not desc_line_match:
            fail("description 字段值无法解析")
            passed = False
        else:
            line_bytes = len(desc_line_match.group(0).encode("utf-8"))
            if line_bytes > DESCRIPTION_LINE_BYTE_LIMIT:
                fail(
                    f"description 整行字节数 {line_bytes} > {DESCRIPTION_LINE_BYTE_LIMIT}"
                    f" (AGENTS.md wc -c 检查)"
                )
                passed = False
            else:
                ok(f"description 整行字节数 {line_bytes} ≤ {DESCRIPTION_LINE_BYTE_LIMIT}")

    if "license:" not in m.group(1):
        fail("frontmatter 缺 license 字段")
        passed = False
    else:
        ok("license 字段存在")

    # 禁用字段
    if re.search(r"^\s*metadata:\s*$", m.group(1), re.MULTILINE):
        # 检查 metadata.internal
        meta_block = re.search(
            r"metadata:\s*\n((?:[ \t]+.+\n)+)", m.group(1)
        )
        if meta_block and re.search(r"^\s*internal:\s*true", meta_block.group(1), re.MULTILINE):
            fail("frontmatter 含 metadata.internal: true (禁止在真实 skill 中使用)")
            passed = False
        else:
            ok("frontmatter 不含 metadata.internal")
    else:
        ok("frontmatter 无 metadata 块")

    # 首行必须是 ---
    first_line = text.split("\n", 1)[0]
    if first_line.strip() != "---":
        fail(f"文件首行不是 --- (实际: {first_line!r})")
        passed = False
    else:
        ok("文件首行 ---")

    return passed


def check_references_exist() -> bool:
    print("\n[2] references/ 文件存在性校验")
    passed = True
    if not REFS_DIR.is_dir():
        fail(f"references/ 目录不存在: {REFS_DIR}")
        return False
    for name in EXPECTED_REFS:
        p = REFS_DIR / name
        if not p.exists():
            fail(f"references/{name} 缺失")
            passed = False
        else:
            pass  # 静默不输出,避免噪音
    if passed:
        ok(f"全部 {len(EXPECTED_REFS)} 个 references 文件存在")
    return passed


def check_mechanism_count() -> bool:
    print(f"\n[3] 14 机制清单计数 (期望 == {EXPECTED_MECHANISM_COUNT})")
    p = REFS_DIR / "02-checklist.md"
    if not p.exists():
        fail("02-checklist.md 不存在")
        return False
    text = p.read_text(encoding="utf-8")
    # 主表里 `| N | **<name>** |` 形式
    mechanisms = re.findall(r"^\|\s*\d+\s*\|\s*\*\*([^*]+)\*\*", text, re.MULTILINE)
    # 排除 Continue Site (WanLanglin §3.2 7 个续跑点)
    core = [m for m in mechanisms if not m.startswith("Continue Site")]
    if len(core) != EXPECTED_MECHANISM_COUNT:
        fail(
            f"02-checklist.md 主表核心机制数 = {len(core)} "
            f"(期望 {EXPECTED_MECHANISM_COUNT})"
        )
        return False
    ok(f"02-checklist.md 主表核心机制数 = {len(core)} == {EXPECTED_MECHANISM_COUNT}")
    return True


def check_antipattern_count() -> bool:
    print(f"\n[4] 30 反模式清单计数 (期望 == {EXPECTED_ANTIPATTERN_COUNT})")
    p = REFS_DIR / "03-antipatterns.md"
    if not p.exists():
        fail("03-antipatterns.md 不存在")
        return False
    text = p.read_text(encoding="utf-8")
    # ### Xn · 标题
    items = re.findall(r"^###\s+([A-Z]\d+)\s+", text, re.MULTILINE)
    if len(items) != EXPECTED_ANTIPATTERN_COUNT:
        fail(
            f"03-antipatterns.md 反模式数 = {len(items)} "
            f"(期望 {EXPECTED_ANTIPATTERN_COUNT})"
        )
        return False
    ok(f"03-antipatterns.md 反模式数 = {len(items)} == {EXPECTED_ANTIPATTERN_COUNT}")
    return True


def check_license_banner() -> bool:
    print("\n[5] WanLanglin license banner 出现次数 ≥ 1")
    # 至少在 04 / 05 / 08 之一出现 "All Rights Reserved" 或 "viewing only"
    keywords = ("All Rights Reserved", "viewing only")
    hits = []
    for name in EXPECTED_REFS:
        p = REFS_DIR / name
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        if any(kw in text for kw in keywords):
            hits.append(name)
    if not hits:
        fail("B4 修复未生效: 任何 references 文件都未出现 WanLanglin license 警告")
        return False
    ok(f"B4 修复已生效: {len(hits)} 个文件含 license 警告 ({', '.join(hits)})")
    return True


def check_shareai_chapter_claim() -> bool:
    print("\n[6] shareAI-lab 章节数声明修正检查 (B4/H1 修复)")
    # 02-checklist.md 和 05-source-synthesis.md 不应再出现 "17 + 17(中/日)" 这种旧声称
    # 但可以出现 "12 × 3(中/英/日)"
    bad_pattern = re.compile(r"17\s*\+\s*17\s*\(中/?/?日?\)")
    bad_files = []
    for name in EXPECTED_REFS:
        p = REFS_DIR / name
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        if bad_pattern.search(text):
            bad_files.append(name)
    if bad_files:
        fail(
            f"shareAI-lab 章节数仍声称 17 + 17(中/日): {', '.join(bad_files)}"
        )
        return False
    ok("shareAI-lab 章节数声称已修正(不再使用 17 + 17)")
    return True


def main() -> int:
    print(f"agent-harness-design 自检 — 目标: {SKILL_DIR}")
    results = [
        check_frontmatter(),
        check_references_exist(),
        check_mechanism_count(),
        check_antipattern_count(),
        check_license_banner(),
        check_shareai_chapter_claim(),
    ]
    print()
    if all(results):
        print("✅ 全部 PASS")
        return 0
    failed = sum(1 for r in results if not r)
    print(f"❌ {failed} 项 FAIL (总计 {len(results)} 项)")
    return 1


if __name__ == "__main__":
    sys.exit(main())