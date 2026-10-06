---
name: brain-audit
description: Vault maintenance pipeline — compile inbox notes, connect via QMD semantic search, generate insights, sync QMD index, produce weekly digest.
user-invocable: true
---

# brain-audit

Manual vault maintenance. Pick the subskill that matches the request; "run brain-audit" / "weekly audit" means the full run below.

| User says | Subskill |
|-----------|----------|
| "compile my notes", "promote pitfalls", "review inbox" | `compile` |
| "promote to sensors", "which rules keep recurring" | `promote` |
| "find connections", "link my notes", "synthesize patterns" | `connect` |
| "insights", "what patterns", "what blockers" | `insights` |
| "knowledge gaps", "what to document", "roadmap", "where are my projects" | `queries` |
| "sync qmd", "reindex vault" | `qmd-sync` |
| "weekly digest", "reset audit clock" | `digest` |

**Full run order:** `qmd-sync` → `compile` → `promote` → `queries` → `connect` → `insights` → `digest` (pass the compile/connect/insights counts to `digest`). `compile`, `promote` and `queries` read files directly; `connect` and `insights` need a fresh QMD index.

Each subskill is `skills/<name>/SKILL.md` under this skill's root (`~/ai-dotfiles/skills/brain-audit/`). Claude Code exposes them as `brain-audit:<name>`; Cursor CLI and Mistral Vibe only see this router, so read the file at that path instead — don't report the subskill as missing.
