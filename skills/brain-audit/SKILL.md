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

After `/capture` completes, suggest: "Run `brain-audit:compile` to promote today's notes to cross-project knowledge?"
