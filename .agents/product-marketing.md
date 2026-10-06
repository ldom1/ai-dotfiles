# Product Marketing Context

**Document version:** v1
**Last updated:** 2026-10-06

## Product Overview
**One-liner:** One Git repo that configures Claude Code, Cursor and Mistral Vibe, plus an Obsidian vault that gives every project a memory the agents load and write back.
**What it does:** Centralises rules, hooks, skills and MCP config for three coding agents across machines. Injects a bounded slice of the vault (project note + cross-project pitfalls) at session start; `/capture` writes each session back.
**Product category:** Agent harness configuration / AI coding agent setup ("dotfiles for AI agents", "Claude Code setup", "harness engineering").
**Product type:** Open-source config repo + Claude Code plugin marketplace (MIT). Personal project, published.
**Business model:** Free. The real "product" for marketing purposes is the author's Medium articles and GitHub repo.

## Target Audience
**Target:** Individual developers and small teams using Claude Code daily, often alongside Cursor or another agent.
**Primary use case:** Stop re-explaining the same context and re-making the same mistakes in every agent session, on every machine and tool.
**Jobs to be done:**
- Make agent rules hold reliably (mechanisms, not prose).
- Keep memory and config outside any vendor's store, in Git and Markdown.
- Reuse skills across tools.

## Problems & Pain Points
**Core problem:** Every agent session starts blank; rules written in prose are followed "most of the time"; config is scattered per tool and per machine.
**Why alternatives fall short:**
- Harness packs (hundreds of files) are hard to understand and to trust.
- Vendor memory features lock memory into one tool.
**Emotional tension:** Not knowing what the agent actually does or remembers ("I felt a bit lost: I had no clear view of what it actually did").

## Competitive Landscape
**Secondary:** Harness packs / starter kits for Claude Code — fast to install, opaque, not portable across tools.
**Secondary:** Vendor-native memory (Claude Code memory, Codex memory) — one tool only.
**Indirect:** OpenClaw-style always-on assistants — author used it 4 months, maintenance cost exceeded use.

## Differentiation
- Rules become hooks where it pays: a guard is shipped only with its limits stated and its noise measured.
- One source (`AGENTS.md`, one skill tree) for three agents.
- Memory in an Obsidian vault in Git, with human gates on writes.
- Every claim backed by a repo file or a measured number.

## Objections
- "Too personal to reuse" → skills install individually from the marketplace; patterns are copyable.
- "More hooks = more friction" → measured: the tripwire prompts 3 times in 60 days of real use.
- "Just use a harness pack" → borrow ideas, not packs; each fix is under ~200 lines.

**Anti-persona:** Someone wanting a turnkey product with support; non-developers.

## Customer Language
**How they describe the problem (author's own words, used in articles):**
- "a rule that holds most of the time wants to be a hook"
- "every AI coding tool starts each session with a blank slate"
- "the same architecture question on a Monday that I had already answered on Thursday"
**Words to use:** harness, hook, guard, rule, memory, vault, measured, tripwire, Claude Code.
**Words to avoid:** "robust solution", "landscape", "delve", "revolutionary", "game-changer".

## Brand Voice
**Tone:** Practical, honest about limits and failures.
**Style:** First person, short sentences, concrete commands and numbers.
**Personality:** Pragmatic, skeptical, precise, self-critical.

## Proof Points
**Metrics (2026-10-06):**
- 58% of agent rules were silently lost at session start; now 0% (8,967 B → 5,136 B, write-time gate).
- Destructive-command tripwire: first draft 18 prompts/day; shipped version 3 prompts in 60 days.
- 9 PRs from one spec, every test red-first; ~230 hook tests.
- Loop scan: 0 loops in 38 transcripts → no loop-cap hook built.
**Value themes:** reliability of rules (proof: budget gate), safety without friction (proof: replay), honesty (proof: documented bypasses, "measured and not built").

## Goals
**Business goal:** Readership and GitHub stars for ai-dotfiles; author credibility in AI agent engineering.
**Conversion action:** Read to the end, clap/follow on Medium, visit the repo.
**Current metrics:** Unknown.

## Changelog
*Newest first. One line per revision: what changed and why.*
- v1 (2026-10-06) — Initial context, auto-drafted from README, AGENTS.md and the two published articles, to audit the harness-review article.
