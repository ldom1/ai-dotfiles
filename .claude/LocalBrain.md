# Local Brain

Obsidian vault, git repo. Path: `$BRAIN_PATH` from `~/ai-dotfiles/config/brain.env`. Hooks pull on SessionStart and commit + push on SessionEnd.

| Path | Holds | Written by |
|---|---|---|
| `inbox/daily/implementation/<project>/YYYY-MM-DD-<topic>.md` | Session logs (the history) | `/capture` |
| `inbox/daily/checkpoints/<project>/YYYY-MM-DD.md` | Pre-compaction breadcrumbs; folded into the session log, then deleted | PreCompact hook → `/capture` |
| `inbox/daily/specs/<project>/…-design.md` · `inbox/daily/plans/<project>/…-plan.md` | Specs · implementation plans | brainstorming / planning |
| `inbox/{connections,insights,qa,drafts}/` | Maintenance output | `/brain-audit` |
| `inbox/sensors/YYYY-MM-DD-<slug>.md` | Sensor drafts for rules hit in ≥ 2 sessions; the user reviews them | `/brain-audit` (`promote`) |
| `projects/<slug>.md` | Project one-pager: idea, objectives, how it works, where (printed at session start) | `ai-dotfiles init`/`upgrade` (skeleton), `/brain-init-project` |
| `resources/operational/ai-agents/pitfalls.md` | Cross-project rules, injected every session (≤ 6,000 B and one id per rule, enforced at write time by `scripts/check-pitfalls-budget.sh`) | `/capture`, `/brain-audit` |
| `resources/operational/ai-agents/archive/` | Frozen incident logs (pre-2026-09-29 pitfalls/lessons) | — |
| `resources/knowledge/{sops,patterns,home-lab,operational}/` | SOPs, infra docs; `patterns/*-patterns.md` `## Rules` hold stack-specific rules (Docker, Python, deployment, observability) | `/brain-audit`, as needed |
| `caps/` | Areas of responsibility | user |
| `meta/` | Digests, `last-maintenance.md` | `/brain-audit` |

Project memory (architecture, decisions, current state) lives in the repo at `<repo>/.claude/memory/`, not in the vault.

Notes: frontmatter `title`, `created`, `tags`, `status`; link with `[[slug]]`.
