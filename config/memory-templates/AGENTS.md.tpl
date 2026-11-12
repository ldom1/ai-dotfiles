# AGENTS.md — Project instructions
# Location : project root (canonical). CLAUDE.md is a symlink → AGENTS.md.
# Scope    : all agents (Claude, Mistral, Codex, …). Claude Code loads it via the symlink.
# Length   : keep under 60 lines — agents read this every session.

---

## Description
<!-- One paragraph: what this project does, tech stack, deployment context. -->

## Key Files
<!-- 3–5 files an agent must know to orient itself. -->

## Task-Specific Behaviors
<!-- Commands to always run, files to read before touching a module, hard rules. -->

## Constraints
<!-- Protected files, dependency policy, hard limits. -->

## Standards
<!-- Reference shared coding standards. Uncomment the relevant line(s): -->
<!-- @.claude/standards/python.md -->

## Memory
<!-- Claude Code loads memory only through these imports (the SessionStart hook skips it).
     Move a line out of the comment below once that file has real content. -->
@.claude/memory/OBJECTIVES.md
@.claude/memory/CONTEXT.md
<!--
@.claude/memory/DESIGN.md
@.claude/memory/ARCHITECTURE.md
@.claude/memory/DECISIONS.md
@.claude/memory/ROADMAP.md
@.claude/memory/API.md
-->
