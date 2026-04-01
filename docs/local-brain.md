# Local Brain — Setup Guide

Local Brain is an Obsidian vault that acts as Claude's persistent memory across all sessions. It is a plain git repo: Claude reads it at session start and writes knowledge back to it during the session.

## 1. Create the vault

Create the folder and open it in [Obsidian](https://obsidian.md):

| Platform | Default path |
|----------|-------------|
| Windows  | `C:\Users\<you>\Documents\Local Brain` |
| WSL      | `/mnt/c/Users/<you>/Documents/Local Brain` |
| macOS    | `/Users/<you>/Documents/Local Brain` |

Init it as a git repo and add a remote:

```bash
cd "/path/to/Local Brain"
git init
git remote add origin git@github.com:<you>/local-brain.git
```

## 2. Create the seed files

```
Local Brain/
├── IDENTITY.md       ← who you are: role, context, preferences
├── breadcrumbs.md    ← running index of key resources and active projects
└── docs/memory/
    └── MEMORY.md     ← Claude's persistent memory (starts empty)
```

## 3. Configure the path

Copy and edit `config/brain.env`:

```bash
cp config/brain.env.example config/brain.env
# Set BRAIN_PATH to your vault location
```

## 4. Symlink Claude's memory into the vault

This makes Claude's auto-memory system write directly into Obsidian:

```bash
mkdir -p "/path/to/Local Brain/docs/memory"
ln -sf "/path/to/Local Brain/docs/memory" \
  "/home/<you>/.claude/projects/-home-<you>/memory"
```

## 5. Point LocalBrain.md to your paths

Update `.claude/LocalBrain.md` with your username:

```
- Vault (WSL) : /mnt/c/Users/<you>/Documents/Local Brain/
- Vault (Windows) : C:\Users\<you>\Documents\Local Brain
- Claude memory : `/home/<you>/.claude/projects/-home-<you>/memory/`
```

Done. Claude will automatically read `IDENTITY.md`, `breadcrumbs.md`, and `docs/memory/MEMORY.md` at the start of every session.

## Vault structure (PARA)

```
Local Brain/
├── IDENTITY.md
├── breadcrumbs.md
├── daily/                      ← daily notes
├── projects/                   ← active project files
├── caps/                       ← long-term areas (developer, student, entrepreneur…)
├── resources/knowledge/
│   ├── architecture/
│   │   ├── plans/              ← YYYY-MM-DD-name.md
│   │   ├── specs/
│   │   └── adr/
│   ├── patterns/
│   ├── operational/            ← tool setups (Claude, MCPs, RTK…)
│   └── sops/
├── docs/
│   ├── memory/MEMORY.md        ← Claude persistent memory
│   └── context/                ← per-session context
├── todo/
└── archive/
```

## What Claude stores where

| Type | Location |
|------|----------|
| Technical decision | `resources/knowledge/architecture/` |
| Spec / design doc | `resources/knowledge/architecture/specs/YYYY-MM-DD-name.md` |
| Implementation plan | `resources/knowledge/architecture/plans/YYYY-MM-DD-name.md` |
| ADR | `resources/knowledge/architecture/adr/` |
| Reusable pattern | `resources/knowledge/patterns/` |
| Tool / setup doc | `resources/knowledge/operational/` |
| Active project | `projects/<name>.md` |
| Daily note | `daily/YYYY-MM-DD.md` |
| Persistent memory | `docs/memory/MEMORY.md` |
| Session context | `docs/context/session-YYYY-MM-DD.md` |

## Note conventions

```yaml
---
title: <title>
created: YYYY-MM-DD
tags: [tag1, tag2]
status: active | archived
---
```

Use `[[wiki-links]]` between related notes.
