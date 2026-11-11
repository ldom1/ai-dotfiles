---
name: brain-audit
description: Vault maintenance pipeline — compile inbox notes, promote recurring pitfalls and harness changes to sensor drafts, run the knowledge-gaps and roadmap queries, connect via QMD semantic search, generate insights, sync QMD index, reset the maintenance clock with a digest.
user-invocable: true
---

# brain-audit

Manual vault maintenance. Pick the subskill that matches the request; "run brain-audit" / "weekly audit" means the full run below.

| User says | Subskill |
|-----------|----------|
| "compile my notes", "promote pitfalls", "review inbox", "synthesize patterns", "create knowledge files" | `compile` |
| "draft sensors", "turn recurring pitfalls into hooks", "which rules keep recurring" | `promote` |
| "find connections", "link my notes" | `connect` |
| "insights", "what patterns", "what blockers" | `insights` |
| "knowledge gaps", "what to document", "roadmap", "where are my projects" | `queries` |
| "sync qmd", "reindex vault" | `qmd-sync` |
| "lint the vault", "unresolved links", "orphans", "broken skill paths" | `lint` (`bash scripts/vault-lint.sh`, no subskill file) |
| "weekly digest", "reset audit clock" | `digest` |

**Full run order:** `qmd-sync` → `compile` → `lint` → `promote` → `queries` → `connect` → `insights` → `digest` (`digest` resets the clock; pass it the counts for the digest note). `compile`, `promote` and `queries` read files directly; `connect` and `insights` need a fresh QMD index. `lint` runs `scripts/vault-lint.sh` (read-only Obsidian CLI: unresolved links, orphans, missing `$BRAIN_PATH/` paths in skills) and needs Obsidian open: the CLI launches it otherwise. `skipped:` means no CLI on this machine; `error:` (exit 1) means the CLI failed. A `warning: Obsidian link cache is stale` line means restart Obsidian, then run `lint` again for exact counts.

Each subskill is `skills/<name>/SKILL.md` under this skill's root (`~/ai-dotfiles/skills/brain-audit/`). Claude Code exposes them as `brain-audit:<name>`; Cursor CLI and Mistral Vibe only see this router, so read the file at that path instead — don't report the subskill as missing.
