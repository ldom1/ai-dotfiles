# Local Brain

Obsidian vault, git repo. Path: `$BRAIN_PATH` from `~/ai-dotfiles/config/brain.env`. Hooks pull on SessionStart and commit + push on SessionEnd.

| Path | Holds | Written by |
|---|---|---|
| `inbox/daily/implementation/<project>/YYYY-MM-DD-<topic>.md` | Session logs (the history). Same thread today: append | `/capture` |
| `inbox/daily/checkpoints/<project>/YYYY-MM-DD.md` | Pre-compaction breadcrumbs. `/capture` folds them into the session log, then deletes them; until then they are pushed with the vault | PreCompact hook → `/capture` |
| `inbox/daily/specs/<project>/…-design.md` · `inbox/daily/plans/<project>/…-plan.md` | Specs · implementation plans | brainstorming / planning |
| `inbox/daily/products/<project>/…` · `inbox/daily/prompts/<project>/…` | Articles and drafts about a product · saved prompts (`_templates/prompt-template.md`) | user |
| `inbox/review/YYYY-MM-DD-<slug>.md` | Review items: an action to do by hand or a choice to make. The user answers there; `TASKS_REVIEW.base` lists them | agents (`/capture`) |
| `inbox/insights/YYYY-MM-DD.md` | Cross-project insight reports | `/brain-audit` (`insights`) |
| `inbox/sensors/YYYY-MM-DD-<slug>.md` | Sensor drafts for rules hit in ≥ 2 sessions; the user reviews them | `/brain-audit` (`promote`) |
| `raw/` | Raw source material dropped by the user; one file, one future note | user |
| `TASKS_REVIEW.base` · `VEILLE.base` | Obsidian views: open review items · tech-watch notes | user |
| `projects/<slug>.md` | Project one-pager: idea, objectives, how it works, where (printed at session start) | `ai-dotfiles init`/`upgrade` (skeleton), `/brain-init-project` |
| `resources/operational/ai-agents/pitfalls.md` | Cross-project rules, injected every session (≤ 6,000 B and one id per rule, enforced at write time by `scripts/check-pitfalls-budget.sh`) | `/capture`, `/brain-audit` |
| `resources/operational/ai-agents/archive/` | Frozen incident logs (pre-2026-09-29 pitfalls/lessons) | — |
| `resources/knowledge/{sops,patterns,home-lab,operational}/` | SOPs, infra docs; `patterns/*-patterns.md` `## Rules` hold stack-specific rules (Docker, Python, deployment, observability) | `/brain-audit`, as needed |
| `resources/knowledge/veille/YYYY-MM-DD-<topic>.md` | Tech-watch recap notes | `veille-technique` |
| `resources/knowledge/veille-technique.md` | Veille verdict ledger | `veille-technique` |
| `_templates/` | Note templates used by `load.sh`, `/capture` and `veille-technique` | user |
| `resources/queries/archive/` | Knowledge-gap and roadmap reports | `/brain-audit` (`queries`) |
| `caps/` | Areas of responsibility | user |
| `meta/` | Digests, `last-maintenance.md` | `/brain-audit` |
| `meta/harness-sessions/<YYYY-MM>-<host>.jsonl` | Per-session harness metrics | SessionEnd hook |
| `archive/` | Retired notes. Move there, never delete | user |

Project memory (architecture, decisions, current state) lives in the repo at `<repo>/.claude/memory/`. `projects/<slug>/` in the vault is a mirror of it (`scripts/sync-project.sh`): edit the repo copy.

Notes: frontmatter `title`, `created`, `tags`, `status`. Link with `[[slug]]`: filename only, no folder, no `.md`. Backlinks and the graph only see wikilinks.

Order of truth, highest first: live state and git, `<repo>/.claude/memory/`, `projects/<slug>.md`, session log, insights and digests. When two sources differ, trust the higher one.

A skill is written `` `name` ``, never `[[name]]`: a skill is not a vault note, so the wikilink stays unresolved.

Vault access per tool:

- Claude Code: hooks (SessionStart and SessionEnd).
- Cursor CLI: `scripts/cursor-agent-brain.sh`.
- Mistral Vibe: `.vibe/bootstrap.md` (the agent runs `sync.sh start` and `load.sh` itself).
- Cursor IDE: none. Run `/brain-load` on request.
