# Brain Load — Expected Vault Layout

The Local Brain vault is an Obsidian vault backed by a git repository. `brain-load` expects the following structure.

## PARA layout (preferred)

```
$BRAIN_PATH/
├── IDENTITY.md            ← who you are: role, context, preferences
├── breadcrumbs.md         ← running index of key resources + active projects
├── daily/                 ← daily notes (YYYY-MM-DD.md)
├── projects/
│   ├── _template.md       ← REQUIRED for auto-instantiation (instantiate.sh reads this)
│   └── <slug>.md          ← one file per active project
├── caps/                  ← long-term areas of responsibility
│   ├── developer.md
│   ├── entrepreneur.md
│   └── <id>.md
├── resources/
│   └── knowledge/
│       ├── architecture/
│       │   ├── plans/     ← YYYY-MM-DD-name.md
│       │   ├── specs/
│       │   └── adr/
│       ├── patterns/
│       ├── operational/   ← tool setups (Claude, RTK, MCPs…)
│       └── sops/
├── docs/
│   ├── memory/
│   │   └── MEMORY.md      ← Claude persistent memory (auto-memory symlink target)
│   └── context/           ← per-session context notes
├── todo/
└── archive/
```

## Legacy layout (fallback)

```
$BRAIN_PATH/
└── Projects/
    └── <slug>/
        └── brief.md       ← created from reference/templates/brief.md
```

`brain-load` detects which layout is present:

- If `projects/` directory or `projects/_template.md` exists → **PARA mode**
- Otherwise → **legacy mode**

## Slug → note path mapping

| Mode | Note path |
|------|-----------|
| PARA | `$BRAIN_PATH/projects/<slug>.md` |
| Legacy | `$BRAIN_PATH/Projects/<slug>/brief.md` |

## Note frontmatter convention

```yaml
---
title: <project name>
created: YYYY-MM-DD
tags: [project, <cap-id>]
caps: [[caps/<cap-id>]]
status: active
---
```

## Required seed files

For full functionality across sessions:

| File | Purpose |
|------|---------|
| `IDENTITY.md` | Claude reads this to understand your role and context |
| `breadcrumbs.md` | Index of active projects and key resources |
| `docs/memory/MEMORY.md` | Claude's persistent memory (starts empty) |
| `projects/_template.md` | Required for `instantiate.sh` auto-creation |

## Claude auto-memory symlink

To make Claude Code's auto-memory write directly into the vault:

```bash
mkdir -p "$BRAIN_PATH/docs/memory"
ln -sf "$BRAIN_PATH/docs/memory" \
  "$HOME/.claude/projects/-home-<you>-<project>/memory"
```

Replace `<you>` and `<project>` with your username and the project directory slug.
