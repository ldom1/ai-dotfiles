# Local Brain

**Single source of truth for every Claude session.**
Canonical vault: `$BRAIN_PATH` (set in `~/ai-dotfiles/config/brain.env`).

## Paths

| Role | Path |
|------|------|
| Vault root | `$BRAIN_PATH` — WSL: `/mnt/c/Users/<you>/Documents/Local Brain/` · macOS: `/Users/<you>/Documents/Local Brain/` |
| Claude memory symlink | `~/.claude/projects/<project-dir>/memory` → `$BRAIN_PATH/docs/memory/` |

## Session reads (in order)

1. `$BRAIN_PATH/IDENTITY.md` — user profile
2. `$BRAIN_PATH/breadcrumbs.md` — quick context index
3. `$BRAIN_PATH/docs/memory/MEMORY.md` — persistent memory
4. Active project: `$BRAIN_PATH/projects/<slug>.md`

## Where to write

| Kind | Location |
|------|----------|
| Architecture, ADR, specs, plans | `resources/knowledge/architecture/` |
| Patterns | `resources/knowledge/patterns/` |
| Ops / Claude / RTK / FinOps | `resources/knowledge/operational/` |
| SOPs | `resources/knowledge/sops/` |
| Active project meta | `projects/<name>.md` |
| Ideas / opportunities | `caps/entrepreneur.md` or `todo/` |
| Daily capture | `daily/YYYY-MM-DD.md` |
| Implementation session log | `inbox/daily/implementation/<slug>/YYYY-MM-DD-topic.md` |
| Persistent memory | `docs/memory/MEMORY.md` |
| Session context | `docs/context/session-YYYY-MM-DD.md` |

Superpowers artifacts (plans, specs) → `resources/knowledge/architecture/plans/` or `specs/`. Never only in a repo's `docs/`.

## Update rules

- **`breadcrumbs.md`** — refresh when a new project starts or a key resource appears
- **`MEMORY.md`** — add durable facts that must carry across sessions
- **Frontmatter** — prefer `title`, `created`, `tags`, `status` on every note
- **Links** — use `[[wiki-links]]` between related notes

## Layout

$BRAIN_PATH/
├── IDENTITY.md
├── breadcrumbs.md
├── inbox/
│   └── daily/
│       └── implementation/  ← implementation session logs by project
├── daily/
├── projects/
├── caps/               ← areas of responsibility
├── todo/
├── resources/knowledge/
│   ├── architecture/   ← plans/, specs/, adr/
│   ├── patterns/
│   ├── operational/
│   └── sops/
├── docs/
│   ├── memory/MEMORY.md
│   └── context/
└── archive/