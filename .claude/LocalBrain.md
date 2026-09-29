# Local Brain

Obsidian vault, git repo. Path: `$BRAIN_PATH` from `~/ai-dotfiles/config/brain.env`. Hooks pull on SessionStart and commit + push on SessionEnd.

| Path | Holds | Written by |
|---|---|---|
| `inbox/daily/implementation/<project>/YYYY-MM-DD-<topic>.md` | Session logs (the history) | `/capture` |
| `inbox/daily/specs/<project>/…-design.md` · `inbox/daily/plans/<project>/…-plan.md` | Specs · implementation plans | brainstorming / planning |
| `inbox/{connections,insights,qa,drafts}/` | Maintenance output | `/brain-audit` |
| `projects/<slug>.md` | Project one-pager: idea, objectives, how it works, where (printed at session start) | `ai-dotfiles init`/`upgrade` (skeleton), `/brain-init-project` |
| `resources/operational/ai-agents/pitfalls.md` | Cross-project rules, injected every session (keep ≤ 6 KB: it shares the hook's ~9.5 KB budget with the project note) | `/capture`, `/brain-audit` |
| `resources/operational/ai-agents/archive/` | Frozen incident logs (pre-2026-09-29 pitfalls/lessons) | — |
| `resources/knowledge/{sops,patterns,home-lab,operational}/` | SOPs, infra docs; `patterns/*-patterns.md` `## Rules` hold stack-specific rules (Docker, Python, deployment, observability) | `/brain-audit`, as needed |
| `caps/` | Areas of responsibility | user |
| `meta/` | Digests, `last-maintenance.md` | `/brain-audit` |

Project memory (architecture, decisions, current state) lives in the repo at `<repo>/.claude/memory/`, not in the vault.

Notes: frontmatter `title`, `created`, `tags`, `status`; link with `[[slug]]`.
