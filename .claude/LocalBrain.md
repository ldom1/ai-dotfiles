# Local Brain — pointer

**Canonical memory** is the Obsidian vault (`BRAIN_PATH` in `~/ai-dotfiles/config/brain.env`).

## Session reads (when a full bootstrap is needed)

1. `$BRAIN_PATH/IDENTITY.md`
2. `$BRAIN_PATH/breadcrumbs.md`
3. `$BRAIN_PATH/docs/memory/MEMORY.md`
4. Active project: `$BRAIN_PATH/projects/<slug>.md`

## Where to write durable facts

| Kind | Location |
|------|----------|
| Ops / Claude / FinOps | `resources/knowledge/operational/` |
| Architecture, ADR, specs | `resources/knowledge/architecture/` |
| Active project meta | `projects/` |
| Daily | `daily/` |

**Superpowers artifacts** (plans, specs): under `resources/knowledge/architecture/` — not only in repo `docs/`.

## Layout

PARA + `docs/memory/`, `docs/context/`, `caps/`, `resources/knowledge/` — see vault root.

## Symlink

Claude project `memory` → `$BRAIN_PATH/docs/memory/` (see `~/ai-dotfiles/docs/local-brain.md`).
