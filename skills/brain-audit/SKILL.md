---
name: brain-audit
description: Vault maintenance pipeline — compile inbox notes, connect via QMD semantic search, generate insights, sync QMD index, produce weekly digest.
user-invocable: true
---

# brain-audit — Context Routing

Route to the appropriate subskill based on what the user is asking:

| User says | Invoke |
|-----------|--------|
| "audit my notes", "weekly audit", "vault maintenance", "run brain-audit" | `brain-audit` (full orchestrator) |
| "compile my notes", "promote pitfalls", "review inbox" | `brain-audit:compile` |
| "find connections", "link my notes", "semantic connections" | `brain-audit:connect` |
| "insights", "what patterns", "what blockers", "synthesize" | `brain-audit:insights` |
| "sync qmd", "update qmd index", "reindex vault" | `brain-audit:qmd-sync` |
| "knowledge gaps", "what am I missing", "what to document" | `brain-audit:queries` |
| "roadmap", "project status", "where are my projects" | `brain-audit:queries` |
| "weekly digest", "generate digest", "reset audit clock" | `brain-audit:digest` |

## Invoking a Subskill

The subskills live at `skills/<name>/SKILL.md` relative to this skill's root — `skills/compile/SKILL.md`,
`skills/connect/SKILL.md`, `skills/insights/SKILL.md`, `skills/qmd-sync/SKILL.md`,
`skills/queries/SKILL.md`, `skills/digest/SKILL.md`.

The `brain-audit:<name>` form in the table above is **Claude Code only**. Cursor CLI and Mistral
Vibe discover skills one level deep, so they see this router and nothing under it. There, **read
the file at the path above instead** — same instructions in context, and the routing table still
decides which one. If a `brain-audit:<name>` is not in your available-skills list, go straight to
the path rather than reporting the subskill as missing.

After `/capture` completes, suggest: "Run `brain-audit:compile` to promote today's notes to cross-project knowledge?"
