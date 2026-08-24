# Awesome Skills (license-gated pointer list)

This document collects pointers to high-quality upstream skills that we cannot install under `skills/`. The repo is MIT-licensed, so skill content must come from upstreams whose license is compatible with MIT; skills without a LICENSE file or under a non-MIT license are tracked here as pointers until upstream licensing is resolved. No upstream prose, scripts, or assets are copied into this repo, and every entry is metadata only: attribution, license status, and a one-line reason the skill does not live in this repository.

A pointer entry lets the next reader find the upstream on their own, install it from its native location if their project license permits, and file an issue upstream asking for a LICENSE if one is missing. It's a discovery aid, not an endorsement of fitness for any particular use; review the upstream's own SKILL.md and scripts before installing anywhere it will run with real credentials.

The list is curated by this repo's maintainers; suggestions arrive as pull requests (see below). If an upstream later publishes a compatible LICENSE, move the entry out of this file and into `skills/<name>/` instead of leaving a stale pointer behind. Discovery inside this repo stops at the pointer; the install decision lives with the reader and their project license.

Order within the file follows upstream addition date (oldest first). When the list outgrows a single file, the layout moves to `docs/awesome-skills/<skill-name>.md` and a generated index; the schema stays the same. Sections are alphabetized once the list passes roughly twenty entries; for the first handful, addition order keeps the git history easier to read.

## Entries

### codebase-to-course

- **Upstream**: [Zara Zhang](https://github.com/zarazhangrui/codebase-to-course)
- **License**: `no LICENSE file in upstream repo as of 2026-08-22`
- **Why not installed**: `Upstream repository has no LICENSE file; license compatibility with this repo's MIT cannot be confirmed, so per AGENTS.md the skill cannot be copied into skills/.`
- **What it does**: Turns any codebase into a single-page interactive HTML course with scroll modules, animations, quizzes, and code↔plain-English side-by-side panels.
- **Use when**: `"turn this into a course"`, `"explain this codebase interactively"`, `"teach me how this code works"`, `"interactive tutorial from this code"`.

### dg-piagent

- **Upstream**: buchidonggua (冬瓜), https://github.com/buchidonggua/dg-ai-notes/tree/main/skills/dg-piagent
- **License**: `repo LICENSE is MIT (code) but README §License + CONTRIBUTING.md §License carve "文档" as CC-BY-SA-4.0; skills/dg-piagent/SKILL.md is "文档" by upstream's own definition; SKILL.md frontmatter has no `license:` field`
- **Why not installed**: `This repo's contribution is a metadata pointer only — we ship zero verbatim prose and zero re-derivative content from upstream. Either form would touch the license gate: verbatim copy falls under upstream's CC-BY-SA-4.0 docs carve-out; re-derivation would still inherit the same source. Adopted federation pattern: agent-harness-design callouts route readers to install dg-piagent themselves for SDK-versioned work.`
- **What it does**: SDK-development assistant for `@earendil-works/pi-coding-agent` v0.83.0 — given a pi-coding-agent task (build a DataAgent, scaffold a tool, wire extension hooks, evaluate an internal LLM endpoint, deploy as an SSE streaming service), dg-piagent returns executable code + API-precise configuration.
- **Use when**: `"调用 pi-coding-agent SDK 直接干活"`, `"为 pi agent 加新的 tool"`, `"接 pi.on 或 session.subscribe 扩展点"`, `"评估自研 LLM 接入 pi-agent"`, `"把 pi agent 包成 SSE 流服务"`.

## How to add an entry

- **Schema**: every block uses the same five fields in this order: Upstream, License, Why not installed, What it does, Use when. Don't add fields beyond the schema; the document stays scannable because every block carries the same shape. Stars, last-updated dates, installable alternatives, and local-copy placeholders are explicitly excluded; if any of them seem useful, the entry belongs in a different file.
- **Self-check**: before opening a PR, confirm a LICENSE file is present at the upstream repo root (or in a clearly-marked `LICENSE.md`) and that its terms are compatible with this repo's MIT. If either check fails, the skill doesn't belong under `skills/` and may only be added here as a pointer.
- **No copying**: quote trigger phrases in lowercase and keep them to one line; don't lift full sentences from the upstream README. A grep against three distinctive upstream phrases (twelve words or more each) must return zero matches before the PR is ready for review.
- **Branch and PR**: one PR per entry. Branch off `main` as `docs/awesome-skills-add-<slug>` where `<slug>` is the upstream skill name in kebab-case. Keep the diff to a single new `### <name>` block; update this section only when the schema itself changes.
- **Future layout**: if the list grows past roughly ten entries, split into per-entry files under `docs/awesome-skills/`. For now, a single Markdown file keeps the diff and review surface small, and a CI walk that stays inside `skills/` is never broken.
- **License resolved**: when an upstream later publishes a compatible LICENSE, remove the entry here and submit a follow-up PR that installs the skill under `skills/<name>/` following the normal create workflow.

The empty template:

```markdown
### <skill-name>

- **Upstream**: <author or org>, <repo URL>
- **License**: <status, e.g. "no LICENSE file in upstream repo as of YYYY-MM-DD">
- **Why not installed**: <one-line reason>
- **What it does**: <one sentence>
- **Use when**: "<trigger>", "<trigger>", "<trigger>"
```
