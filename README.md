# ai-dotfiles

[![CI](https://github.com/ldom1/ai-dotfiles/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ldom1/ai-dotfiles/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/ldom1/ai-dotfiles?sort=semver)](https://github.com/ldom1/ai-dotfiles/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Wiki](https://img.shields.io/badge/docs-wiki-blue)](https://github.com/ldom1/ai-dotfiles/wiki)

A personal AI control centre with two jobs: **centralise** Claude Code / Cursor / Mistral Vibe config across machines, and give every project a **persistent knowledge layer** backed by an Obsidian vault — so the agent always starts with structured context instead of a blank slate.

---

## Install a skill

```
/plugin install brain-sync@ldom1/ai-dotfiles
/plugin install brain-load@ldom1/ai-dotfiles
/plugin install brain-search@ldom1/ai-dotfiles
/plugin install brain-route@ldom1/ai-dotfiles
/plugin install brain-audit@ldom1/ai-dotfiles
/plugin install capture@ldom1/ai-dotfiles
/plugin install brain-init-project@ldom1/ai-dotfiles
/plugin install create-pr@ldom1/ai-dotfiles
/plugin install grill-me@ldom1/ai-dotfiles
/plugin install sop-builder@ldom1/ai-dotfiles
/plugin install server-audit@ldom1/ai-dotfiles
/plugin install graphify@ldom1/ai-dotfiles
/plugin install finops-audit@ldom1/ai-dotfiles
```

| Skill | Purpose |
|-------|---------|
| [brain-sync](https://github.com/ldom1/ai-dotfiles/wiki/Skills/Brain-Sync) | Sync Local Brain Obsidian vault at session start/end |
| [brain-load](https://github.com/ldom1/ai-dotfiles/wiki/Skills/Brain-Load) | Load / instantiate project notes from vault |
| [brain-search](https://github.com/ldom1/ai-dotfiles/wiki/Skills/Brain-Search) | Semantic + keyword search over vault via qmd (`scripts/search.sh`) |
| [brain-route](https://github.com/ldom1/ai-dotfiles/wiki/Skills/Brain-Route) | Session router: maintenance vs normal (used after brain-sync pull) |
| [brain-audit](https://github.com/ldom1/ai-dotfiles/wiki/Skills/Brain-Audit) | Four-phase vault maintenance (raw → digest) |
| capture | End-of-session workflow: implementation notes, project-brain review, pitfalls/lessons, sync |
| [create-pr](https://github.com/ldom1/ai-dotfiles/wiki/Skills/Create-PR) | GitHub PR with branch + commit conventions |
| grill-me | Stress-test plans through one-question-at-a-time design interrogation |
| sop-builder | Turn process notes into validated seven-section SOP documents |
| [server-audit](https://github.com/ldom1/ai-dotfiles/wiki/Skills/Server-Audit) | Infra audit: parallel checks and JSON reports |
| [graphify](https://github.com/ldom1/ai-dotfiles/wiki/Skills/Graphify) | `/graphify` — folder → knowledge graph; also [graphify.net](https://graphify.net/) |
| [finops-audit](https://github.com/ldom1/ai-dotfiles/wiki/Skills/FinOps-Audit) | Weekly token spend review → vault |

Wiki hub: **[Skills](https://github.com/ldom1/ai-dotfiles/wiki/Skills)** (catalogue). Keep wiki pages directly in the local **`.wiki/`** clone (GitHub wiki repo) under the **`Skills/`** namespace (e.g. `Skills/Brain-Sync`), then publish explicitly with:

```bash
# one-time setup:
git clone https://github.com/ldom1/ai-dotfiles.wiki.git .wiki

# publish:
bash scripts/update-wiki.sh
```

**Full documentation → [Wiki](https://github.com/ldom1/ai-dotfiles/wiki)**

---

## Frontend & design skills

Five design/frontend skills are pre-enabled by default via `.claude/settings.json.tpl` (regenerated into `.claude/settings.json` by `scripts/install.sh` on every machine) — no manual `/plugin install` needed after `git pull` + re-running install. They come from three different sources and cover distinct, complementary stages of building a visual artifact:

| Skill | Source | Role |
|-------|--------|------|
| `frontend-design` | `claude-plugins-official` (Anthropic) | Production-grade UI code for real apps — avoids generic "AI-generated" look. Use for actual app screens/components. |
| `web-artifacts-builder` | `example-skills@anthropic-agent-skills` ([anthropics/skills](https://github.com/anthropics/skills)) | Bundles a multi-component React + Tailwind + shadcn/ui build into a single self-contained HTML artifact. Use for interactive claude.ai artifacts. |
| `canvas-design` | `example-skills@anthropic-agent-skills` | Static visual art — posters, social graphics, cover images — as PDF/PNG, via a "design philosophy first" workflow. |
| `algorithmic-art` | `example-skills@anthropic-agent-skills` | Generative/procedural art via p5.js — flow fields, particle systems, fractals, seeded randomness. |
| `ui-ux-pro-max` | `ui-ux-pro-max-skill` ([nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill), third-party) | Design-intelligence lookup: color palettes, font pairings, UX guidelines, chart types. Feeds decisions *into* the other four rather than producing output itself. |

**Why they're complementary, not redundant:** `ui-ux-pro-max` supplies the design decisions (palette, typography, layout guideline); `frontend-design` and `web-artifacts-builder` turn those decisions into working UI code (a real app vs. a self-contained artifact, respectively); `canvas-design` and `algorithmic-art` cover static and generative *visual art* rather than UI — different output shape (PDF/PNG image) than the code-producing skills. Claude picks the matching skill from the task's output shape (app screen vs. artifact vs. static image vs. generative art vs. "what palette should I use").

`example-skills` bundles more than the three listed here (`mcp-builder`, `webapp-testing`, `theme-factory`, etc.) — installing the one plugin gives access to all of them.

`web-artifacts-builder`, `canvas-design`, and `algorithmic-art` come from Anthropic's official examples repo but are **not** part of `claude-plugins-official` (Claude Code's built-in marketplace) — they need `anthropic-agent-skills` registered as a known marketplace, which `settings.json.tpl` now does via `extraKnownMarketplaces`. Same pattern for the third-party `ui-ux-pro-max-skill` marketplace.

To pick these up on a machine that already ran `install.sh` before this change: `git pull && bash scripts/install.sh` (idempotent — regenerates `settings.json` from the template). You don't have to remember this yourself — the `SessionStart` hook (`brain-session-start.sh`) compares `settings.json` against `settings.json.tpl` on every session and re-runs `install.sh` automatically if it's behind, logging to `.claude/logs/brain-load.log`. New plugins from an auto-heal become active starting the *next* session, since Claude Code reads `settings.json` before the hook runs.

---

## Project brain sync

Each project can carry a persistent knowledge layer — git-tracked in the project repo and mirrored in the Local Brain vault — so the agent always loads structured context without manual prompting.

### Prerequisites

| Tool | Install | Required for |
|------|---------|--------------|
| `jq` | `apt install jq` / `brew install jq` | Central + per-project MCP settings merge |
| `uvx` | `pip install uv` | Running code-index-mcp (zero install) |
| `qmd` | `npm install -g @tobilu/qmd` | Semantic search over brain vault |

### QMD vault setup (one-time)

First, add `source ~/ai-dotfiles/config/brain.env` to your `~/.zshrc` (or `~/.bashrc`) so that `BRAIN_PATH` and `QMD_INDEX_PATH` are exported into every shell and inherited by Claude Code hooks:

```bash
echo 'source ~/ai-dotfiles/config/brain.env' >> ~/.zshrc
```

Then initialise the central embedding database:

```bash
source ~/ai-dotfiles/config/brain.env
mkdir -p "$(dirname "$QMD_INDEX_PATH")"
INDEX_PATH="$QMD_INDEX_PATH" qmd collection add "$BRAIN_PATH" --name brain
INDEX_PATH="$QMD_INDEX_PATH" qmd context add "qmd://brain" "Local Brain vault"
INDEX_PATH="$QMD_INDEX_PATH" qmd update --collection brain
INDEX_PATH="$QMD_INDEX_PATH" qmd embed --collection brain
```

After this, Claude can query vault notes semantically from any initialized project. The index and embeddings refresh automatically at session end via `brain-sync` (`qmd update` then `qmd embed`).

### Setup

```bash
# 1. Tag the project
echo "my-project" > /path/to/project/.brain-project

# 2. Initialise
ai-dotfiles init /path/to/project
```

This creates `<project>/.claude/memory/` with template files, mirrors them to `$BRAIN_PATH/projects/my-project/`, and registers the project in `config/brain-projects.tsv`. `brain-sync` then keeps both sides in sync automatically at session start/end.

### Centrally-managed MCP servers

`qmd`, `code-index-mcp`, and `graphify` are registered once, globally, instead of
being copy-pasted into every project:

- Claude Code: `~/.claude.json` (user scope) — all three servers
- Cursor: `~/.cursor/mcp.json` (global scope) — `qmd` only (see note below)

`ai-dotfiles init` / `ai-dotfiles upgrade` apply this automatically. Run
`ai-dotfiles mcp-sync` any time to re-apply by hand — e.g. after editing
`config/memory-templates/mcp-central-claude.json.tpl` or
`mcp-central-cursor.json.tpl`, or as a first-time bootstrap on a new machine. Each
sync fully replaces its own managed keys and leaves every other `mcpServers` entry
untouched; a `.bak` copy of the target file is written before every merge.

Project-specific servers (e.g. a project's own RapidAPI key) stay in that project's
own `.mcp.json` / `.cursor/mcp.json` — only servers meant for every project belong in
the central templates.

`code-index-mcp` and `graphify` rely on `${CLAUDE_PROJECT_DIR}` (Claude Code's own
per-session path variable) to resolve the active project from a global-scope entry.
Cursor's equivalent global-scope behavior is unconfirmed, so those two stay
per-project there instead: `graphify`'s Cursor entry is written by the graphify skill
per project; there's no Cursor entry for `code-index-mcp` at all.

### Knowledge files

| File | Purpose | When to update |
|------|---------|----------------|
| `OBJECTIVES.md` | Goals, scope, non-goals | Written once, refined rarely |
| `DESIGN.md` | Original application intent, UX, and durable product workflows | When product/design intent changes |
| `ARCHITECTURE.md` | Stack decisions, key modules | When architecture changes |
| `DECISIONS.md` | Append-only ADR log | After every significant decision |
| `CONTEXT.md` | Current state: done / in-progress / open questions | At session end |
| `ROADMAP.md` | Feature backlog and priorities | When priorities shift |
| `API.md` | External contracts and endpoints | When API changes |

`DESIGN.md` is the durable product/application baseline: original intent, UX, and workflows. `ARCHITECTURE.md` is the live technical map: stack, modules, data flow, and implementation trade-offs.

`settings.json` controls which files are injected by `brain-load` at session start (`read_on_session_start`, defaults to `OBJECTIVES.md` + `CONTEXT.md`). The rest are loaded on demand.

### Memory format

Each knowledge file follows [Open Knowledge Format](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing) conventions, adapted for agentic context (see also [Interpretable Context Methodology, 2025](https://arxiv.org/abs/2603.16021)):

- **Typed frontmatter** — `type:` and `updated:` fields on every file, enabling version-aware tooling and graph-level queries across the vault
- **Token budget** — a `<!-- keep this file under ~N words -->` comment per template guides Claude to keep context files lean for session injection
- **Backward-compatible evolution** — `upgrade` backfills missing frontmatter and new `## sections` from the template into existing files without touching content (`scripts/merge-memory-md.py`)
- **Cross-links over duplication** — `brain-init-project` instructs Claude to link related entries across files (e.g., `DECISIONS.md → ARCHITECTURE.md`) instead of repeating content

### Commands

```bash
ai-dotfiles init <path>              # initialise + register
ai-dotfiles upgrade <path>           # add missing files, backfill frontmatter and sections
ai-dotfiles upgrade --all            # upgrade all registered projects
ai-dotfiles sync <path>              # manual bidirectional rsync
ai-dotfiles sync --all               # sync all registered projects
ai-dotfiles merge-memory <path>      # backfill OKF frontmatter + missing sections only (no file additions)
ai-dotfiles merge-memory --all       # merge all registered projects
ai-dotfiles mcp-sync                 # (re)apply centrally-managed MCP servers (qmd, code-index, graphify)
```

`merge-memory` is the focused variant of `upgrade`: it runs only the structural backfill step (`merge-memory-md.py`) on existing files, without adding new files or touching MCP settings. Use it when you want to bring an older project's memory files up to the current template structure without triggering a full upgrade.

### Automatic sync (brain-sync)

`brain-sync start` pulls vault → project for all registered paths. `brain-sync end` pushes project → vault before the vault git commit. Strategy: `rsync --update` (newer mtime wins, no merge). Unregistered projects are skipped silently.

---

## Personal setup (quick start)

```bash
git clone git@github.com:<you>/ai-dotfiles.git ~/ai-dotfiles
bash ~/ai-dotfiles/scripts/install.sh
```

`install.sh` symlinks `~/.claude` and `~/.cursor` to this repo, generates `settings.json` from the template, and creates `settings.local.json` if missing. Skills are wired automatically — no plugin install needed for your own machine. It also sets `git config core.hooksPath git-hooks` so the versioned [pre-commit hook](git-hooks/pre-commit) runs (blocks accidental commits under Cursor runtime dirs under `.cursor/` and scans staged diffs for secrets). If you clone without running `install.sh`, run `bash scripts/install-git-hooks.sh` once from the repo root.

`settings.json` is now versioned in this repo (while still generated by `install.sh` from `.claude/settings.json.tpl`).

## Design principle

**The AI tools never know about ai-dotfiles.** Files inside `.claude/`, `.cursor/`, `.vibe/` are written as if they are the native config directories (`~/.claude`, `~/.cursor`, etc.). They contain no references to the repo structure, no "ai-dotfiles" framing, no awareness of the versioning layer. Skills invoke scripts via `~/ai-dotfiles/skills/…` because that's the real filesystem path — but config files never explain *why* things are at that path.

## Structure

```
ai-dotfiles/
├── AGENTS.md                        # symlink → .vibe/AGENTS.md (Vibe discovery)
├── .claude/
│   ├── CLAUDE.md                    # Global instructions (tool-native, no ai-dotfiles refs)
│   ├── LocalBrain.md                # Vault layout pointer
│   ├── RTK.md                       # RTK reference
│   ├── skills/                      # symlinks → ../../skills/<name> (Claude Code)
│   ├── settings.json.tpl            # Settings template (HOME placeholder)
│   ├── settings.local.json.example  # Machine-specific permissions template
│   └── hooks/
│       └── rtk-rewrite.sh           # PreToolUse: rtk rewrite + tail cap on noisy output
├── .cursor/
│   ├── rules/                       # brain-sync, brain-load, finops-claude, graphify-context (.mdc)
│   └── skills                       # symlink → ../skills (shared skill source)
├── .vibe/
│   ├── AGENTS.md                    # Mistral Vibe bootstrap (canonical)
│   ├── README.md                    # Vibe skill discovery and trust
│   └── skills/                      # symlinks → skills/* (Mistral Vibe discovery)
├── skills/
│   ├── brain-sync/                  # Sync Local Brain at session start/end
│   │   ├── SKILL.md
│   │   ├── scripts/sync.sh
│   │   └── reference/
│   ├── brain-load/                  # Load / instantiate Local Brain project notes
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   └── reference/
│   ├── brain-search/                # /brain-search — semantic + keyword vault search
│   │   ├── SKILL.md
│   │   └── scripts/search.sh        # search.sh [--mode search|vsearch|query] "<query>"
│   ├── graphify/                    # /graphify — corpus → knowledge graph
│   │   ├── SKILL.md
│   │   ├── .claude-plugin/plugin.json
│   │   └── skills/graphify/SKILL.md -> ../../SKILL.md
│   ├── create-pr/                   # /create-pr — gh + git conventions
│   │   ├── SKILL.md
│   │   └── reference/GIT-COMMITS.md
│   └── server-audit/                # /server-audit — robust server audit
│       ├── SKILL.md
│       ├── scripts/audit.sh
│       ├── scripts/check_*.sh
│       ├── scripts/aggregate.py
│       ├── config/targets.json.example
│       ├── .claude-plugin/plugin.json
│       └── skills/server-audit/SKILL.md -> ../../SKILL.md
├── config/
│   ├── brain.env.example            # Local Brain path template
│   ├── brain.env                    # Your config (gitignored)
│   ├── brain-projects.tsv           # Registry of projects with a .claude/memory/ folder
│   ├── memory-templates/            # OKF-typed templates copied on `ai-dotfiles init`
│   │   ├── settings.json            # Agent instructions + read_on_session_start list
│   │   ├── OBJECTIVES.md            # type: objectives — goals, scope, non-goals
│   │   ├── DESIGN.md                # type: design — original intent, UX, durable workflows
│   │   ├── ARCHITECTURE.md          # type: architecture — stack, modules, decisions log
│   │   ├── DECISIONS.md             # type: decisions — append-only ADR entries
│   │   ├── CONTEXT.md               # type: context — current state snapshot
│   │   ├── ROADMAP.md               # type: roadmap — milestones and priorities
│   │   └── API.md                   # type: api — external contracts and endpoints
│   ├── graphify.env.example         # Optional: GRAPHIFY_PROJECT for uv-based graphify clone
│   └── graphify.env                 # Your graphify clone path (gitignored)
├── .github/
│   └── workflows/
│       ├── ci.yml                   # Shellcheck, JSON validation, skill structure
│       └── release.yml              # GitHub Release on v* tags
├── .wiki/                           # Local clone of GitHub wiki repo (source for wiki pages)
├── LICENSE
├── CONTRIBUTING.md
├── prompts/
├── bin/
│   └── ai-dotfiles                  # CLI: init / upgrade / sync / merge-memory
└── scripts/
    ├── install.sh                   # Setup script (symlinks, settings, hooks, CLI)
    ├── init-project.sh              # Initialise a project brain folder
    ├── upgrade-project.sh           # Add missing files, backfill frontmatter + sections
    ├── merge-memory.sh              # Backfill OKF frontmatter + missing sections only
    ├── merge-memory-md.py           # Per-file merge: adds frontmatter + ## headers non-destructively
    ├── sync-project.sh              # Bidirectional rsync for registered projects
    └── update-wiki.sh               # Commit/push local .wiki/ changes
```

> **Note — nested `skills/<name>/skills/<name>/SKILL.md`**
>
> Inside each skill folder there is a nested symlink:
> `skills/brain-load/skills/brain-load/SKILL.md → ../../SKILL.md`
>
> This is intentional. The Claude Code marketplace targets the declared source folder
> (`./skills/brain-load`) and looks for a `skills/<name>/SKILL.md` pattern *inside* it.
> The symlink redirects to the real `SKILL.md` — no content is duplicated. **Do not delete it.**

---

## Dependencies

| Tool | Purpose | Install |
|------|---------|---------|
| [Claude Code](https://claude.ai/code) | AI coding assistant (core runtime) | See site |
| [rtk](https://github.com/ldom1/rtk) | Token-saving CLI proxy for Claude Code hooks | `cargo install rtk` |
| [ccusage](https://github.com/ryoppippi/ccusage) | Claude Code token & cost usage dashboard | `npx ccusage` |
| [shellcheck](https://www.shellcheck.net) | Shell script linter (CI + local) | `brew install shellcheck` / `apt install shellcheck` |
| [gh](https://cli.github.com) | GitHub CLI — used by `create-pr` skill | `brew install gh` / `apt install gh` |
| [jq](https://jqlang.github.io/jq) | JSON processor — required by rtk hook | `brew install jq` / `apt install jq` |
| [Python 3](https://www.python.org) | Template substitution in `brain-load` | Pre-installed on most systems |
| [Obsidian](https://obsidian.md) | Browse the Local Brain vault | See site |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © Louis Giron
