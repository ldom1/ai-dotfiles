# ai-dotfiles

[![CI](https://github.com/ldom1/ai-dotfiles/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ldom1/ai-dotfiles/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/ldom1/ai-dotfiles?sort=semver)](https://github.com/ldom1/ai-dotfiles/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Wiki](https://img.shields.io/badge/docs-wiki-blue)](https://github.com/ldom1/ai-dotfiles/wiki)

A personal AI control centre with two jobs: **centralise** Claude Code / Cursor / Mistral Vibe config across machines, and give every project a **persistent knowledge layer** backed by an Obsidian vault. Claude Code and the Cursor Agent CLI load a bounded slice of it at session start; Cursor IDE Agent and Vibe load it on demand. `/capture` writes each session back as a log you can read, search and audit.

---

## Install a skill

```
/plugin install brain-sync@ldom1/ai-dotfiles
/plugin install brain-load@ldom1/ai-dotfiles
/plugin install brain-search@ldom1/ai-dotfiles
/plugin install brain-audit@ldom1/ai-dotfiles
/plugin install capture@ldom1/ai-dotfiles
/plugin install brain-init-project@ldom1/ai-dotfiles
/plugin install grill-me@ldom1/ai-dotfiles
/plugin install git-promotion@ldom1/ai-dotfiles
/plugin install sop-builder@ldom1/ai-dotfiles
/plugin install photo-archive-triage@ldom1/ai-dotfiles
/plugin install server-audit@ldom1/ai-dotfiles
/plugin install graphify@ldom1/ai-dotfiles
/plugin install finops-audit@ldom1/ai-dotfiles
```

| Skill | Purpose |
|-------|---------|
| [brain-sync](https://github.com/ldom1/ai-dotfiles/wiki/Skills/Brain-Sync) | Sync Local Brain Obsidian vault (Claude Code hooks; Cursor CLI via `cursor-agent-brain.sh` alias; manual via skill) |
| [brain-load](https://github.com/ldom1/ai-dotfiles/wiki/Skills/Brain-Load) | Load / instantiate project notes from vault |
| [brain-search](https://github.com/ldom1/ai-dotfiles/wiki/Skills/Brain-Search) | Semantic + keyword search over vault via qmd (`scripts/search.sh`) |
| [brain-audit](https://github.com/ldom1/ai-dotfiles/wiki/Skills/Brain-Audit) | Four-phase vault maintenance (raw → digest) |
| capture | End-of-session workflow: session log, project memory snapshot, cross-project pitfall rules, sync |
| grill-me | Stress-test plans through one-question-at-a-time design interrogation |
| git-promotion | Promote develop → preprod → main (or a PR straight onto main) with a semver tag and GitHub Release; stages, tag prefix, gate and changelog per repo in `.git-promotion.json` |
| medium-writer | Draft a Medium article from real repo code into `articles/`, then write it onto its Notion task page |
| ponytail | Lazy senior mode — YAGNI ladder, stdlib before deps, minimum code that works (`/ponytail`) |
| asd-ste100 | Rewrite a doc in ASD-STE100 Simplified Technical English (strict or STE-flavored), with a stdlib linter (`scripts/ste-lint.py`) |
| sop-builder | Turn process notes into validated seven-section SOP documents |
| photo-archive-triage | Non-destructive photo/video triage: exact dedup, corrupt screening, capture-date recovery |
| [server-audit](https://github.com/ldom1/ai-dotfiles/wiki/Skills/Server-Audit) | Infra audit: parallel checks and JSON reports |
| [graphify](https://github.com/ldom1/ai-dotfiles/wiki/Skills/Graphify) | `/graphify` — folder → knowledge graph; also [graphify.net](https://graphify.net/) |
| [finops-audit](https://github.com/ldom1/ai-dotfiles/wiki/Skills/FinOps-Audit) | Weekly token spend review → vault |
| marketingpowers | `/marketingpowers` — router over six marketing sub-skills; enforces `product-marketing` first and the order the rest run in |

`graphify` is vendored from [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) (the `SKILL.md` + `reference/` files, adapted with two local additions: the `GRAPHIFY_PROJECT` local-clone fallback and default-on agent-MCP auto-wiring via `scripts/setup_agent_mcp.py`). The synced upstream release is tracked in `skills/graphify/.graphify_version` — re-diff against that tag before syncing again to isolate local customizations from upstream changes.

`marketingpowers` is a **router plugin**: `skills/marketingpowers/SKILL.md` decides which marketing sub-skill to run and in what order, and `references/campaign-sequence.md` holds the ordered full-campaign playbook. Both are local, not upstream.

The six sub-skills under `skills/marketingpowers/skills/` — `product-marketing`, `launch`, `copywriting`, `directory-submissions`, `competitors`, `marketing-psychology` — are vendored from [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) `v2.11.1` (MIT, © Corey Haines) — `SKILL.md` + `references/` only; upstream `evals/` fixtures dropped. They surface as `marketingpowers:<name>`. Single shared pin for all six: `skills/marketingpowers/.marketingskills_version`. One local patch: the `../../tools/integrations/introw.md` link in `launch/SKILL.md` is rewritten to an absolute upstream URL (the partner `tools/` tree is not vendored). Re-syncing the six does not touch the router.

| Sub-skill | Purpose |
|-----------|---------|
| product-marketing | Product/ICP/positioning context doc (`.agents/product-marketing.md`) — **runs first**; every other sub-skill reads it |
| launch | Launch planning: ORB framework, readiness gate, Product Hunt playbook, post-launch cadence |
| copywriting | Landing/home/pricing page copy — frameworks, hero structure, CTA and value-prop work |
| directory-submissions | Directory + review-site layer of a launch: backlinks, GEO, destination pages, submission tracker |
| competitors | `vs` / `alternative` comparison pages for SEO and positioning |
| marketing-psychology | Mental models + cognitive biases as a lens for copy, pricing and offers — never a deliverable on its own |

`product-marketing` writes `.agents/product-marketing.md` into the **target project** repo, not into ai-dotfiles. Paid ads, cold email, sales decks, mobile app-store listings, SMS and referral programs are deliberately **not** vendored.

**Cross-harness caveat.** Nested sub-skills resolve only in Claude Code, as `marketingpowers:<name>`. Cursor CLI and Mistral Vibe discover skills one level deep, so they load the router and nothing beneath it. Both routers (`marketingpowers` and `brain-audit`) therefore document the relative `skills/<name>/SKILL.md` path and instruct the agent to read the file directly when the namespaced form is unavailable — reading it puts the same instructions in context that invoking it would.

**Pitfall-to-sensor promotion.** `/capture` writes a `**Pitfall hit:** [[pitfalls#^<id>]]` line in the session log for each Absorb or Improve verdict. `/brain-audit` runs `promote` after `compile`. It counts distinct sessions per rule id in the lookback window (`skills/brain-audit/scripts/count-pitfall-hits.py BRAIN_PATH [--days N]`). It writes a sensor draft to `inbox/sensors/` for each id hit in 2 sessions or more. The digest lists the drafts. Nothing installs itself: you accept a draft by asking for it as a normal task.

`ponytail` is vendored from [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) (`skills/ponytail/SKILL.md` only — on-demand skill, not the upstream alwaysApply Cursor rule). Pin: `skills/ponytail/.ponytail_version`. Re-sync: diff against the pinned tag, apply upstream, bump the pin (same pattern as graphify; no local patches today). The upstream `ponytail-review` / `-audit` / `-debt` / `-gain` / `-help` sub-skills are not vendored.

`asd-ste100` is vendored from [danyuchn/asd-ste100-skill](https://github.com/danyuchn/asd-ste100-skill) (MIT): `SKILL.md`, `references/`, `examples/`, `scripts/ste-lint.py`, `LICENSE`. It ships no copy of ASD's dictionary (not redistributable). Upstream has no releases, so the pin `skills/asd-ste100/.ste100_version` is a commit SHA and `config/vendored-skills.json` tracks `"branch": "master"`: the update check compares the pin to the branch head. The always-on part of the docs style is the 6-line `## Docs style (80% ASD-STE100)` block in `AGENTS.md`; this skill is the on-demand rewrite pass.

### Vendored skill update checks

SessionStart (Claude + Cursor Agent CLI) runs `scripts/check-vendored-skill-updates.sh`: compares pins in `config/vendored-skills.json` to each repo’s GitHub **latest release** (cache: `~/.claude/cache/vendored-skill-updates.json`, default **24h**, fail-open). Fetches run in parallel (shared 3s budget). If a pin is behind, a short WARNING is injected into session context and appended to `.claude/logs/vendored-skill-updates.log`. Transient fetch failures do not freeze the cache for a full day (short retry TTL).

This does **not** auto-upgrade — alert only. Re-sync stays manual (diff pin→tag, replace `skills/<name>/`, bump pin, CHANGELOG, `install.sh`). Register new upstreams in `config/vendored-skills.json`. Force refresh: delete the cache file, then start a session or run `bash scripts/check-vendored-skill-updates.sh --inject`.

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

Six design/frontend skills are available by default, from two different mechanisms:

| Skill | Mechanism | Source | Role |
|-------|-----------|--------|------|
| `impeccable` | Plugin (`impeccable`) | [pbakaus/impeccable](https://github.com/pbakaus/impeccable), successor to Anthropic's `frontend-design` | Production-grade UI code for real apps — 59 deterministic anti-pattern detectors plus a live-browser polish/audit/critique loop (`/impeccable polish`, `/impeccable audit`, etc.), aimed squarely at generic "AI slop" output. Installs a `PostToolUse`(Edit\|Write)+`Stop` hook that scans touched UI files every session (Node ≥22 required; self-disables with a message otherwise, never blocks a turn on error). |
| `taste-skill` | Plugin (`taste-skill`) | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill), third-party | 14 bundled skills for opinionated, committed style directions (brutalist, minimalist, soft, redesign, stitch, image-to-code, image-gen variants) — pick a direction directly instead of combinatorially picking from a lookup table. |
| `web-artifacts-builder` | Local skill (`skills/`) | Vendored from [anthropics/skills](https://github.com/anthropics/skills) | Bundles a multi-component React + Tailwind + shadcn/ui build into a single self-contained HTML artifact. Use for interactive claude.ai artifacts. |
| `canvas-design` | Local skill (`skills/`) | Vendored from `anthropics/skills` | Static visual art — posters, social graphics, cover images — as PDF/PNG, via a "design philosophy first" workflow. |
| `algorithmic-art` | Local skill (`skills/`) | Vendored from `anthropics/skills` | Generative/procedural art via p5.js — flow fields, particle systems, fractals, seeded randomness. |
| `mcp-builder` | Local skill (`skills/`) | Vendored from `anthropics/skills` | Guide for building well-designed MCP servers (Python/FastMCP or Node/TS SDK) that expose external services as tools. |

**Why they're complementary, not redundant:** `taste-skill` supplies an opinionated style direction; `impeccable` and `web-artifacts-builder` turn that direction into working UI code (a real app vs. a self-contained artifact, respectively) and catch generic-looking output along the way; `canvas-design` and `algorithmic-art` cover static and generative *visual art* rather than UI — different output shape (PDF/PNG image) than the code-producing skills; `mcp-builder` is orthogonal — it's for building MCP servers, not visual output. Claude picks the matching skill from the task's output shape.

*Replaced `frontend-design` + `ui-ux-pro-max` with `impeccable` + `taste-skill` (2026-08-25): both complaints driving the swap — generic "AI slop" output and too much manual palette/font-pairing lookup — are exactly what `impeccable`'s anti-pattern detectors and `taste-skill`'s committed style directions target.*

**Two enablement mechanisms, deliberately:**
- `impeccable` and `taste-skill` are registered as Claude Code **plugins** via `extraKnownMarketplaces` in `.claude/settings.json.tpl` (merged into `settings.json` by `scripts/install.sh`), but **disabled globally**: their skill listings and impeccable's per-edit hook cost context in every non-UI session. Enable them per frontend project in its `.claude/settings.json` (committed) or `.claude/settings.local.json` (personal) — project settings override user settings:
  ```json
  { "enabledPlugins": { "impeccable@impeccable": true, "taste-skill@taste-skill": true, "vercel@claude-plugins-official": true } }
  ```
- `web-artifacts-builder`, `canvas-design`, `algorithmic-art`, and `mcp-builder` are vendored as **local skills** under `skills/<name>/SKILL.md`, cherry-picked from Anthropic's `example-skills` plugin (which bundles 17 skills — `docx`, `pdf`, `webapp-testing`, `theme-factory`, etc. — most unwanted here). `scripts/install.sh` auto-symlinks any `skills/<name>` with a `SKILL.md` into `.claude/skills/`, `.vibe/skills/`, and `.cursor/skills/`, so no plugin/marketplace entry is needed for these four, and no unwanted skills come along for the ride. See "Skill discovery across tools" below for how that linking works.

To pick these up on a machine that already ran `install.sh` before this change: `git pull && bash scripts/install.sh` (idempotent — resymlinks `skills/`, regenerates `settings.json` from the template). You don't have to remember this yourself — the `SessionStart` hook (`brain-session-start.sh`) compares `settings.json` against `settings.json.tpl` on every session and re-runs `install.sh` automatically if only plugins or marketplaces are behind, logging to `.claude/logs/brain-load.log`. For new permissions, `env` or hooks it only prints `[install-check] template adds: <keys>`: run `install.sh` yourself. New plugins from an auto-heal become active starting the *next* session, since Claude Code reads `settings.json` before the hook runs; local skills under `skills/` are picked up as soon as `install.sh` resymlinks them.

### Skill discovery across tools

Every skill under `skills/<name>/` is symlinked by `scripts/install.sh` into three per-tool directories — `.claude/skills/<name>`, `.vibe/skills/<name>`, `.cursor/skills/<name>` — one flat loop, same rule for all three: link it if `skills/<name>/SKILL.md` exists, skip it if the name matches `coe-*`.

`coe-*` is reserved for internal/company skills synced locally by a separate, gitignored `scripts/sync-coe-skills.sh` — never committed to this repo (`skills/coe-*`, `.claude/skills/coe-*`, `.vibe/skills/coe-*`, `.cursor/skills/coe-*` are all in `.gitignore`). The `install.sh` filter keeps them out of all three tools' runtime view too, not just out of git — a `coe-*` skill present locally is invisible to Claude Code, Vibe, and Cursor alike until the exclusion is deliberately lifted.

(Prior to this, `install.sh`'s skill loop had no `coe-*` filter at all — `.claude/skills`/`.vibe/skills` linked every skill unconditionally, and `.cursor/skills` was a single symlink to the whole `skills/` directory. `coe-*` was kept out of git via `.gitignore`, but a `coe-*` skill present locally was fully visible to all three tools at runtime. The filter above is what actually enforces the exclusion now, for all three.)

### Skill usage log

Invocations append to `~/.claude/skill-usage.log` (`date skill [source]`):

| Source tag | When |
|------------|------|
| *(none)* / `claude:Skill` | Claude Code `Skill` tool (`PreToolUse` → `.claude/hooks/log-skill-usage.sh`) |
| `claude:sessionStart` / `cursor:sessionStart` / … | Hook-driven `brain-sync` / `brain-load` via `scripts/log-skill-usage.sh` |
| `cursor:skill-read` | Cursor Agent `preToolUse`/`Read` of a `**/skills/**/SKILL.md` (heuristic — exploratory reads count too) |

**Not counted:** alwaysApply `.mdc` rules, SessionStart prompt injection, memory-only follow-through, Vibe (its hooks do not log skill use). Cursor counts are approximate; do not delete skills from Cursor lines alone.

B0 observation artifacts: `spikes/cursor-b0-*` (logger + live sample).

---

## Security review & pentesting skills

| Skill | Mechanism | Source | Role |
|-------|-----------|--------|------|
| `find-security-vulnerabilities-in-code` | Local skill (`skills/`) | Vendored from [usestrix/strix](https://github.com/usestrix/strix) | White-box AI security review — reads the source, then exploits what it finds in a Docker sandbox so every reported issue has a working proof-of-concept, not a static-analysis guess. Only invoke against a local path/repo you own; the SKILL.md itself gates on this — see below. |
| `fix-security-vulnerabilities-with-strix` | Local skill (`skills/`) | Vendored from `usestrix/strix` | Triage Strix findings by severity, patch the root cause, re-run Strix to prove the fix actually closes the exploit. |

Both wrap the [Strix](https://github.com/usestrix/strix) open-source CLI (Apache-2.0) — install separately with `curl -sSL https://strix.ai/install | bash` or `pipx install strix-agent`; requires Docker and an `STRIX_LLM`/`LLM_API_KEY` pair. Strix's own README disclaims unauthorized use but doesn't enforce it at runtime — it will point real exploit execution at whatever target string it's given. `find-security-vulnerabilities-in-code`'s SKILL.md adds an explicit gate on top: only run against a local path or a repo you own, and stop to confirm authorization if a bare external hostname/domain/IP is named instead.

Only these 2 of Strix's 9 upstream skills are vendored — the rest ([usestrix/strix/skills](https://github.com/usestrix/strix/tree/main/skills)) are either thinner wrappers around the same engine or cover per-project decisions (CI PR-gating, the managed app.strix.ai cloud) that don't belong in a shared dotfiles skill set. Read the upstream repo directly if a specific project wants one of those.

---

## Project brain sync

Each project can carry a persistent knowledge layer — git-tracked in the project repo and mirrored in the Local Brain vault. Where session hooks run (Claude Code, Cursor Agent CLI), the agent loads it without manual prompting.

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

`qmd` must run on the same Node major that compiled its native deps (`better-sqlite3`). If Cursor (or another tool) injects a different `node` earlier on `PATH`, `qmd doctor` / `qmd embed` fail with `NODE_MODULE_VERSION` mismatch. Keep nvm's default Node first (`.zshenv` / end of `.zshrc` prepend `$NVM_BIN`); `brain-sync` also prepends the directory that hosts the `qmd` shim before embed.

### Setup

```bash
# 1. Tag the project
echo "my-project" > /path/to/project/.brain-project

# 2. Initialise
ai-dotfiles init /path/to/project
```

This creates `<project>/.claude/memory/` with template files, mirrors them to `$BRAIN_PATH/projects/my-project/`, and registers the project in `config/brain-projects.tsv`. `brain-sync` keeps both sides in sync when session hooks run (Claude Code always; Cursor Agent CLI with prewarm wrapper) — not automatically in Cursor IDE Agent.

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
| `DESIGN.md` *(on demand)* | Original application intent, UX, and durable product workflows | When product/design intent changes |
| `ARCHITECTURE.md` | Stack decisions, key modules | When architecture changes |
| `DECISIONS.md` | Append-only ADR log | After every significant decision |
| `CONTEXT.md` | Current state: done / in-progress / open questions | At session end |
| `ROADMAP.md` | Feature backlog and priorities | When priorities shift |
| `API.md` *(on demand)* | External contracts and endpoints | When API changes |

`init` skips the two *on demand* files: copy them from `config/memory-templates/on-demand/` when a project has a product UX or a public API. `DESIGN.md` is the durable product/application baseline: original intent, UX, and workflows. `ARCHITECTURE.md` is the live technical map: stack, modules, data flow, and implementation trade-offs.

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

`brain-sync start` pulls vault → project for all registered paths. `brain-sync end` pushes project → vault before the vault git commit. Strategy: `rsync --update` (newer mtime wins, no merge). If both copies of one file changed since the last sync, the older edit is overwritten; the vault's git history keeps committed versions. Unregistered projects are skipped silently.

**Who runs it:**

| Tool | Session automation |
|------|-------------------|
| **Claude Code** | Automatic — `.claude/hooks/brain-session-start.sh` / `brain-session-end.sh` (unchanged) |
| **Cursor IDE Agent** | **Off** — no automatic sync, load, or pitfalls injection |
| **Cursor Agent CLI** | **On by default** — see [Cursor Agent CLI brain hooks](#cursor-agent-cli-brain-hooks) below |

Invoke the `brain-sync` / `brain-load` skills manually when hooks are off or the user asks.

### Claude Code hooks

All hooks are declared in `.claude/settings.json.tpl` and always on:

- **SessionStart** `brain-session-start.sh`: settings drift check, vault pull, project note, pitfalls, vendored-skill update check, `/brain-audit` nudge. Output stays under 9.5 KB: Claude Code (observed on 2.1) swaps longer hook output for a file and a 2 KB preview, so pitfalls get only the bytes left and are cut at a line break. The last-exit log shrinks to one status line. Pitfalls are capped at 6,000 B when written (`scripts/check-pitfalls-budget.sh`); if the budget still runs out, whole sections are dropped and named.
- **SessionEnd** `brain-session-end.sh`: vault commit + push, warning if today has no session log. It gives the model no turn: run `/capture` before you quit.
- **PreToolUse (Bash)** `hardline-check.py` (runs first): a tripwire for a short list of destructive commands. It is not a security boundary: it does not see variables, other interpreters or scripts written to a file.
  - Tier 1 (`deny`, in every mode): `rm -rf` on `/` or home, `mkfs`, `dd` or a redirect to a device, `find -delete` from `/` or home, a fork bomb. If you really want one, check the target, then run it yourself with `!`. The deny reason never repeats the command, so you cannot paste it by mistake.
  - Tier 2 (`ask`): force push to `main`/`master`, `git clean -x`/`-d` on the whole tree, `docker system|volume prune`, `docker volume rm`, `chmod -R 777`, a download piped to a shell. A tier-1 shape with a `$` or backtick target also asks.
  - Rules: `.claude/hooks/hardline-rules.json`. The hook header lists the known bypasses, and the tests assert that they pass.
  - `scripts/replay-bash-rules.py --days 14` replays past Bash calls through the rules and the template `ask` list. It prints the prompts per rule, session and day, and every prompt with an empty TP/FP label column.
- **PreToolUse (Bash)** `rtk-rewrite.sh`: rewrites commands to shrink their output.
- **PreToolUse (Bash)** `git-commit-check.sh`: rejects an off-list `type(scope)` in a `git commit -m` message. A heredoc or file message only gets a reminder.
- **PreToolUse (Skill)** `log-skill-usage.sh`: appends to `~/.claude/skill-usage.log`.
- **Stop / PreCompact**: the three sensor hooks below.

#### Sensor hooks

| Event | Script | What it does |
|-------|--------|--------------|
| Stop | `stop-check.sh` | If the repo has `.claude/stop-check` (one shell command) and the git tree has changes, runs it (`STOP_CHECK_TIMEOUT`, default 120 s). On failure it blocks the stop and returns the last 40 lines to the agent. It never blocks twice in a row (`stop_hook_active`); a timeout warns only. Runs are logged to `~/.claude/logs/stop-check.log`. |
| Stop | `compact-nudge.sh` | Reads the last request's context size from the transcript. Past 250k tokens (`COMPACT_NUDGE_START`), then every 100k (`COMPACT_NUDGE_STEP`), shows a one-line `/compact` reminder. Once per step per session. |
| PreCompact | `precompact-checkpoint.sh` | Appends trigger, context size, branch, changed files and the last 3 human prompts to `$BRAIN_PATH/inbox/daily/checkpoints/<slug>/YYYY-MM-DD.md`. `/capture` folds it into the session log, then deletes it. |

Opt a project into the Stop check:

```bash
echo 'ruff check . && pytest -x -q' > .claude/stop-check   # this repo uses shellcheck on changed *.sh
```

`.claude/stop-check` is a shell command that runs with your user's permissions at the end of every agent turn that left changes. A cloned repo can ship one, so the hook runs it only after you approve it:

```bash
! stop-check-trust          # in the Claude Code prompt, from the repo: prints the command, records the approval
stop-check-trust --list     # show all approvals
stop-check-trust --revoke   # remove the approvals of this repo
```

- Before approval, the hook skips the check, never blocks, and shows one message per session.
- The approval covers the command, not the file. A new command needs a new approval. Comment, blank-line, indentation and CRLF edits do not.
- Approvals live in `~/.claude/stop-check-trust` (`<sha256> <repo id>`). Worktrees of one repo share them.
- The template denies `stop-check-trust` to the agent. Read the command before you approve it.

Tests: `.claude/hooks/tests/` (part of the git-promotion gate).

### Shared agent rules (AGENTS.md)

`AGENTS.md` at the repo root is the single source of the rules Claude Code, Cursor and Mistral Vibe share. `.claude/CLAUDE.md` imports it (`@~/ai-dotfiles/AGENTS.md`) and adds Claude-only lines. `scripts/build-agent-rules.sh` (run by `install.sh`) generates `.cursor/rules/agents.mdc` (alwaysApply) and `.vibe/AGENTS.md` (`.vibe/bootstrap.md` + `AGENTS.md`); `install.sh` links `~/.vibe/AGENTS.md` to it, so Vibe gets the rules in every project. CI fails if a generated copy is stale. Edit `AGENTS.md`, never the generated files.

### Stack rules by path (Claude Code)

Stack rules live in the vault at `resources/knowledge/patterns/*-patterns.md`. A note with a `paths:` list in its frontmatter becomes a Claude Code rule:

- `install.sh` runs `scripts/link-pattern-rules.sh`. It symlinks each such note into `.claude/rules/<name>.md` (gitignored) and removes links whose note lost `paths:`.
- Claude Code loads the rule when Read, Write or Edit touches a matching file under the session's working directory. It does not load at launch, so SessionStart output does not grow.
- A Bash command such as `cat Dockerfile` or `git add .gitignore` does not trigger a rule. A file outside the working directory does not trigger a user-level rule.
- The links point at the notes, so rule edits are live. Run `install.sh` again after you add or remove `paths:` on a note.

Cursor and Vibe get no equivalent.

### Cursor Agent CLI brain hooks

Cursor **user hooks** (`.cursor/hooks.json`) run brain sync on the **Agent CLI** — not IDE Agent, not Cloud/remote IDE (`CURSOR_CODE_REMOTE=true` → skip).

**Turn-1 context:** use the zsh alias from **any directory** (no `cd` required):

```bash
alias agent='~/ai-dotfiles/scripts/cursor-agent-brain.sh'   # already in ~/.zshrc
agent   # from anywhere
```

Prewarm writes a global user rule `~/.cursor/rules/brain-hooks-session-inject.mdc` (alwaysApply) + sidecar. It does **not** touch repo-root `AGENTS.md` (the single source of shared rules). Verify: quote `[brain-hooks] sessionStart OK` without Reading files.

### Mistral Vibe hooks

`install.sh` links `~/.vibe/hooks.toml` to `.vibe/user-hooks.toml`. Vibe then runs three Claude Code sensors:

| Vibe hook | Type | Claude Code hook |
|-----------|------|------------------|
| `hardline` | `pre_tool` (bash), `strict` | `hardline-check.py` |
| `commit-scope` | `pre_tool` (bash), `strict` | `git-commit-check.sh` |
| `stop-check` | `post_agent`, 180 s | `stop-check.sh` |

`scripts/vibe-claude-hook.py <hook>` runs each one and translates the protocol:

- A Claude `deny` or Stop `block` becomes a Vibe `deny`. Exit 2 also becomes a `deny`, with stderr as the reason.
- A Claude `ask` becomes a `deny` that tells the model to ask the user. Vibe has no ask decision.
- `allow` and empty output pass. `systemMessage` becomes `system_message`.
- Any other output, or another exit code, is an adapter error (exit 1, details on stderr). The two `strict` hooks then deny the bash call.

Differences from Claude Code:

- A `stop-check` deny injects a retry message. Vibe allows 3 retries per hook per turn, then ends the turn.
- Vibe has no session-start hook. The vault sync and load stay manual (`.vibe/bootstrap.md`).

The file is not named `.vibe/hooks.toml`. In this trusted repo, Vibe would load it twice and warn about each duplicate hook name.

---

## Personal setup (quick start)

```bash
git clone git@github.com:<you>/ai-dotfiles.git ~/ai-dotfiles
cp ~/ai-dotfiles/config/brain.env.example ~/ai-dotfiles/config/brain.env
# edit brain.env: BRAIN_PATH (your vault, a git repo) and QMD_INDEX_PATH
bash ~/ai-dotfiles/scripts/install.sh
echo 'source ~/ai-dotfiles/config/brain.env' >> ~/.zshrc
```

Then index the vault once ([QMD vault setup](#qmd-vault-setup-one-time)) and tag each project ([Setup](#setup)).

Local Medium/blog drafts belong in `articles/` (gitignored).

`install.sh` symlinks `~/.claude` and `~/.cursor` to this repo, generates `settings.json` from the template, and creates `settings.local.json` if missing. Skills are wired automatically — no plugin install needed for your own machine. It also sets `git config core.hooksPath git-hooks` so the versioned [pre-commit hook](git-hooks/pre-commit) runs (blocks accidental commits under Cursor runtime dirs under `.cursor/` and scans staged diffs for secrets). If you clone without running `install.sh`, run `bash scripts/install-git-hooks.sh` once from the repo root.

Run `install.sh` from the main checkout only. It exits with code 2 in a linked git worktree, because the links would point into the worktree and break when it is removed. It also exits with code 2 on an unknown argument, so a flag from a newer version never runs a full install.

`settings.json` is now versioned in this repo (while still generated by `install.sh` from `.claude/settings.json.tpl`).

`install.sh` merges the template's plugins, marketplaces, `permissions.deny`/`ask`, `env` and `hooks` into an existing `settings.json` (`scripts/merge-settings.py`). It keeps local-only entries and `settings.json.bak`. A semantic conflict (different `env` value, same hook command with another event/matcher/timeout, `disableAllHooks: true`) stops the install with exit 3 and leaves `settings.json` unchanged. Run `bash scripts/install.sh --dry-run-settings` to see the planned changes and conflicts without writing anything.

## Local CI

Run a repo's GitHub workflows locally with `act`, in a clean clone of one commit.

```bash
bash scripts/install-act.sh
bash scripts/build-ci-runner.sh
bin/local-ci install --repo <path> --workflows ci.yml
bin/local-ci run --event pull_request --pr <N>
```

The merge guard is off until `git config local-ci.guard true`.

## Design principle

**The AI tools never know about ai-dotfiles.** Files inside `.claude/`, `.cursor/`, `.vibe/` are written as if they are the native config directories (`~/.claude`, `~/.cursor`, etc.). They contain no references to the repo structure, no "ai-dotfiles" framing, no awareness of the versioning layer. Skills invoke scripts via `~/ai-dotfiles/skills/…` because that's the real filesystem path — but config files never explain *why* things are at that path.

## Structure

```
ai-dotfiles/
├── AGENTS.md                        # Shared rules for all three tools (single source)
├── .claude/
│   ├── CLAUDE.md                    # @~/ai-dotfiles/AGENTS.md + Claude-only rules (hooks, session)
│   ├── LocalBrain.md                # Vault layout pointer
│   ├── RTK.md                       # RTK reference
│   ├── skills/                      # symlinks → ../../skills/<name> (Claude Code, coe-* excluded)
│   ├── agents/                      # Subagents: lookup (Haiku), reviewer (Sonnet)
│   ├── rules/                       # symlinks → vault *-patterns.md notes with paths: (gitignored)
│   ├── settings.json.tpl            # Settings template (HOME placeholder)
│   ├── settings.local.json.example  # Machine-specific permissions template
│   └── hooks/
│       ├── brain-session-start.sh   # SessionStart: vault pull, project note, pitfalls (≤ 9.5 KB)
│       ├── brain-session-end.sh     # SessionEnd: vault commit + push, session-log warning
│       ├── hardline-check.py        # PreToolUse: deny/ask tripwire for destructive commands
│       ├── hardline-rules.json      # Rules for hardline-check.py
│       ├── rtk-rewrite.sh           # PreToolUse: rtk rewrite + tail cap on noisy output
│       ├── git-commit-check.sh      # PreToolUse: reject off-list commit scopes
│       ├── log-skill-usage.sh       # PreToolUse (Skill): append to ~/.claude/skill-usage.log
│       ├── stop-check.sh            # Stop: run the repo's .claude/stop-check, block on failure
│       ├── compact-nudge.sh         # Stop: /compact reminder past 250k tokens
│       └── precompact-checkpoint.sh # PreCompact: checkpoint to the vault
├── .cursor/
│   ├── hooks.json                   # User hooks: sessionStart/End → brain-sync + brain-load (CLI default)
│   ├── hooks/                       # session-start.sh, session-end.sh, lib-*.sh
│   ├── rules/                       # agents.mdc (generated from AGENTS.md) + Cursor-only rules (.mdc)
│   └── skills/                      # symlinks → ../skills/<name> (Cursor, coe-* excluded)
├── .vibe/
│   ├── AGENTS.md                    # generated: bootstrap.md + AGENTS.md (~/.vibe/AGENTS.md links here)
│   ├── bootstrap.md                 # Vibe-only sync/load steps (Vibe has no session-start hook)
│   ├── user-hooks.toml              # Vibe hooks (~/.vibe/hooks.toml links here): hardline, commit-scope, stop-check
│   ├── README.md                    # Vibe skill discovery and trust
│   └── skills/                      # symlinks → skills/* (Mistral Vibe, coe-* excluded)
├── skills/
│   ├── brain-sync/                  # Sync Local Brain (Claude/CLI hooks; manual skill)
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
│   └── server-audit/                # /server-audit — robust server audit
│       ├── SKILL.md
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
│   │   ├── ARCHITECTURE.md          # type: architecture — stack, modules, decisions log
│   │   ├── DECISIONS.md             # type: decisions — append-only ADR entries
│   │   ├── CONTEXT.md               # type: context — current state snapshot
│   │   ├── ROADMAP.md               # type: roadmap — milestones and priorities
│   │   └── on-demand/               # DESIGN.md, API.md — copied by hand when a project needs them
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
│   ├── ai-dotfiles                  # CLI: init / upgrade / sync / merge-memory
│   └── stop-check-trust             # approve a repo's .claude/stop-check command
└── scripts/
    ├── cursor-agent-brain.sh        # prewarm inject rule + agent (turn-1 reliable)
    ├── brain-hooks-prewarm.sh       # write alwaysApply inject + sidecar
    ├── install.sh                   # Setup script (symlinks, settings, hooks, CLI)
    ├── init-project.sh              # Initialise a project brain folder
    ├── upgrade-project.sh           # Add missing files, backfill frontmatter + sections
    ├── merge-memory.sh              # Backfill OKF frontmatter + missing sections only
    ├── merge-memory-md.py           # Per-file merge: adds frontmatter + ## headers non-destructively
    ├── replay-bash-rules.py         # Replay past Bash calls through hardline-check (prompt count)
    ├── vibe-claude-hook.py          # Run a Claude Code hook as a Vibe hook (protocol adapter)
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
| [jq](https://jqlang.github.io/jq) | JSON processor — required by rtk hook | `brew install jq` / `apt install jq` |
| [Python 3](https://www.python.org) | Template substitution in `brain-load` | Pre-installed on most systems |
| [Obsidian](https://obsidian.md) | Browse the Local Brain vault | See site |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © Louis Giron
