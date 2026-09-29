# Brain Load — Vault Layout

Full vault map: `~/ai-dotfiles/.claude/LocalBrain.md`. This file covers only what `load.sh` / `instantiate.sh` depend on.

```
$BRAIN_PATH/                  (git repo, Obsidian vault)
├── _templates/
│   └── project-template.md   ← read by instantiate.sh (Templater placeholders)
├── projects/
│   ├── <slug>.md             ← project one-pager, printed at session start
│   └── <slug>/               ← mirror of <repo>/.claude/memory/ (scripts/sync-project.sh)
├── caps/<id>.md              ← areas of responsibility (developer, entrepreneur, Artelys…)
└── inbox/daily/implementation/<slug>/   ← session logs — the only place history goes
```

**Mode detection:** `projects/` or `_templates/project-template.md` exists → PARA (`projects/<slug>.md`); otherwise legacy (`Projects/<slug>/brief.md`, from `templates/brief.md`). On `/mnt/c` the filesystem is case-insensitive, so `Projects/` and `projects/` are the same folder.

**One-pager** (`projects/<slug>.md`, ≤ 450 words, rewritten in place — no journal, no current-state section):

```yaml
---
title: <project name>
created: YYYY-MM-DD
tags: [project]
caps: "[[<cap-id>]]"
status: active
path: <repo path>
prod: <live URL or empty>
---
```

Body: `> one sentence` · `## Idea` · `## Objectives` (goal, users, success, non-goals) · `## How it works` · `## Where` · `## Memory` · `## Links`. Canonical skeleton: `scripts/instantiate.sh`.
