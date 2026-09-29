# Local Brain

Obsidian vault, git repo. Path: `$BRAIN_PATH` from `~/ai-dotfiles/config/brain.env`. Hooks pull on SessionStart and commit + push on SessionEnd.

| Path | Holds | Written by |
|---|---|---|
| `inbox/daily/implementation/<project>/YYYY-MM-DD-<topic>.md` | Session logs (the history) | `/capture` |
| `inbox/daily/specs/<project>/…-design.md` · `inbox/daily/plans/<project>/…-plan.md` | Specs · implementation plans | brainstorming / planning |
| `inbox/{connections,insights,qa,drafts}/` | Maintenance output | `/brain-audit` |
| `projects/<slug>.md` | Project one-pager: idea, objectives, how it works, where (printed at session start) | `ai-dotfiles init`/`upgrade` (skeleton), `/brain-init-project` |
| `resources/operational/ai-agents/pitfalls.md` | Cross-project rules, injected every session (≤ 10 KB) | `/capture`, `/brain-audit` |
| `resources/operational/ai-agents/archive/` | Frozen incident logs (pre-2026-09-29 pitfalls/lessons) | — |
| `resources/knowledge/{sops,patterns,home-lab,operational}/` | SOPs, patterns, infra docs | as needed |
| `caps/`, `todo/`, `kanban/` | Areas of responsibility, ideas, tasks | user |
| `meta/` | Digests, `last-maintenance.md` | `/brain-audit` |
| `docs/memory/MEMORY.md` | Vault-level memory index | as needed |

Project memory (architecture, decisions, current state) lives in the repo at `<repo>/.claude/memory/`, not in the vault.

Notes: frontmatter `title`, `created`, `tags`, `status`; link with `[[slug]]`.
