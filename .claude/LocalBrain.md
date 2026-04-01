# Local Brain — hub

**Local Brain is the single source of truth for every Claude session.**

## Paths (customize)

1. Set `BRAIN_PATH` in `~/ai-dotfiles/config/brain.env` to your vault’s absolute path.
2. Keep the list below in sync with that vault so session-start reads stay explicit.

| Role | Path |
|------|------|
| Vault root | `$BRAIN_PATH` (examples: WSL `/mnt/c/Users/<you>/Documents/Local Brain/`, Windows `C:\Users\<you>\Documents\Local Brain`, macOS `/Users/<you>/Documents/Local Brain`) |
| Claude memory (symlink) | `~/.claude/projects/<claude-project-dir>/memory` → should point at `$BRAIN_PATH/docs/memory/` (see [docs/local-brain.md](../docs/local-brain.md)) |

## Mandatory session start

At the beginning of each session, read in order:

1. `$BRAIN_PATH/IDENTITY.md` — who the user is  
2. `$BRAIN_PATH/breadcrumbs.md` — quick L2 context  
3. `$BRAIN_PATH/docs/memory/MEMORY.md` — persistent memory  

If a specific project is in scope, also read its note under `projects/`.

## Where to store information

Anything learned in a session **must** be stored in Local Brain:

| Information type | Where |
|------------------|--------|
| Technical decision, architecture | `resources/knowledge/architecture/` |
| Spec / design doc | `resources/knowledge/architecture/specs/YYYY-MM-DD-name.md` |
| Implementation plan (superpowers) | `resources/knowledge/architecture/plans/YYYY-MM-DD-name.md` |
| ADR | `resources/knowledge/architecture/adr/` |
| Reusable pattern | `resources/knowledge/patterns/` |
| Tool / setup doc | `resources/knowledge/operational/` |
| SOP, procedure | `resources/knowledge/sops/` |
| Active project | `projects/<name>.md` |
| Idea / opportunity | `caps/entrepreneur.md` or `todo/` |
| Session note | `daily/YYYY-MM-DD.md` |
| Claude persistent memory | `docs/memory/MEMORY.md` |
| Session context | `docs/context/session-YYYY-MM-DD.md` |

## Superpowers — plans and specs in Local Brain

When superpowers skills produce artifacts (plans, specs, ADRs), they belong in the vault:

- **`superpowers:writing-plans`** → create the plan at `resources/knowledge/architecture/plans/YYYY-MM-DD-<name>.md`
- **`superpowers:brainstorming`** → if a design/spec emerges, save it under `resources/knowledge/architecture/specs/`
- **After implementation** → update plan status and the project note in `projects/`
- **Never** put plans/specs only in `~/docs/superpowers/` or a repo’s `docs/` — the vault is the canonical place

**Vault path for superpowers artifacts:**

```
$BRAIN_PATH/resources/knowledge/architecture/
├── plans/          ← implementation plans
├── specs/          ← design docs, technical specs
└── adr/            ← Architecture Decision Records
```

## Update rules

- **breadcrumbs.md** — refresh when a new project starts or a key resource appears  
- **MEMORY.md** — add durable facts that should carry across sessions  
- **Links** — use `[[wiki-links]]` between related notes  
- **Frontmatter** — prefer `title`, `created`, `tags`, `status` on notes  

## PARA layout

```
Local Brain/
├── IDENTITY.md             ← L1: user profile
├── breadcrumbs.md          ← L2: quick index
├── daily/                  ← daily capture
├── projects/               ← short-horizon actions
├── caps/                   ← long-term areas of responsibility
│   ├── developer.md
│   ├── student.md
│   └── entrepreneur.md
├── resources/knowledge/    ← L3: deep reference
│   ├── architecture/
│   ├── patterns/
│   ├── operational/        ← lab, Claude, MCPs, RTK…
│   └── sops/
├── docs/                   ← Claude-oriented files
│   ├── memory/MEMORY.md    ← L1 memory
│   └── context/            ← session context
├── todo/
└── archive/
```
