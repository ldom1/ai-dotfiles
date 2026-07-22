# Changelog

## [Unreleased]

### Added
- Six frontend/design skills available by default via two mechanisms: `frontend-design` and `ui-ux-pro-max` (third-party, [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)) as Claude Code plugins in `.claude/settings.json.tpl`/`extraKnownMarketplaces`; `web-artifacts-builder`, `canvas-design`, `algorithmic-art`, and `mcp-builder` vendored as local skills under `skills/<name>/` (cherry-picked from Anthropic's `example-skills` plugin / [anthropics/skills](https://github.com/anthropics/skills), which bundles 17 skills total — most not wanted here), auto-symlinked into `.claude/skills/` by `scripts/install.sh`. See README "Frontend & design skills" for how the six compose.
- `brain-session-start.sh` (SessionStart hook) now detects when `settings.json` is behind `settings.json.tpl` (new `enabledPlugins`/`extraKnownMarketplaces` keys) and automatically re-runs `scripts/install.sh` — so forgetting to re-run install after a `git pull` self-heals on the next session instead of silently missing new plugins.

### Changed
- `scripts/install.sh`'s skill-linking loop now symlinks `skills/<name>` into `.cursor/skills/<name>` per-skill (same as `.claude/skills/`/`.vibe/skills/`), replacing the old single `.cursor/skills -> ../skills` directory symlink. The loop now also skips any skill matching `coe-*` for all three tools, so internal/company skills synced locally (via the separate, gitignored `scripts/sync-coe-skills.sh`) are excluded from Claude Code, Vibe, and Cursor's runtime view alike — previously the `coe-*` `.gitignore` rules only kept them out of git, not out of any tool's local skill list. See README "Skill discovery across tools".
- Added `.vibe/skills/coe-*` to `.gitignore` (previously only `.claude/skills/coe-*` and `.cursor/skills/coe-*` were listed).

### Fixed
- Added missing Claude plugin metadata for `sop-builder` so the skill structure CI check passes.
- Allowed standard merge commit messages in the git-commit hook.
- Added `ansible/server-setup` detection markers to the git-commit scope registry.

## [0.3.0] - 2026-07-18

### Added
- `DESIGN.md` project memory template for original application intent, UX, and durable workflows, kept distinct from live technical `ARCHITECTURE.md`
- `grill-me` skill for stress-testing plans and designs through one-question-at-a-time interrogation with recommended answers
- `brain-audit` refactored as a plugin with 6 independent subskills (`compile`, `connect`, `insights`, `queries`, `qmd-sync`, `digest`) following the superpowers plugin pattern
- `brain-audit:compile` — reads `inbox/daily/` (last 30 days), promotes cross-project pitfalls/lessons to `resources/operational/ai-agents/`, asks inline for ambiguous entries
- `brain-audit:connect` — QMD `vsearch` per note → appends `[[wikilinks]]`, shows git diff for review
- `brain-audit:insights` — QMD hybrid query per template → writes `inbox/insights/YYYY-MM-DD.md`
- `brain-audit:qmd-sync` — `qmd update` with prune reporting, triggers re-embed if stale
- `brain-audit:queries` — two structured vault analyses: knowledge-gaps (coverage survey vs. recent implementation notes) and roadmap (consolidated status from `projects/*/ROADMAP.md` + recent follow-ups); archives to `resources/queries/archive/`
- `brain-audit:digest` — weekly summary to `meta/digest-YYYY-MM-DD.md`, resets maintenance clock
- **MCP server centralization**: `qmd`, `code-index-mcp`, and `graphify` are now registered once at Claude Code's user scope (`~/.claude.json`) and — `qmd` only — Cursor's global scope (`~/.cursor/mcp.json`), instead of being copy-pasted into every project. New `ai-dotfiles mcp-sync` command (re)applies them by hand. `ai-dotfiles init`/`ai-dotfiles upgrade` no longer write `qmd`/`code-index` into a new project's `.claude/settings.json`; the graphify skill no longer writes a per-project Claude Code entry into `.mcp.json` either (its Cursor entry is unchanged, still per-project). Forward-only: already-initialized projects keep their existing per-project entries untouched. Corrects the claim above — `~/.claude/claude.json` (note the extra `.claude/` segment) is not a path Claude Code actually reads; the real global-scope location is `~/.claude.json` (home root, confirmed via https://code.claude.com/docs/en/mcp).

### Changed
- `.gitignore` now excludes Claude daemon/job runtime state plus last cleanup/update result markers
- `/capture` now reviews project implementation notes against `ARCHITECTURE.md`, `DECISIONS.md`, `ROADMAP.md`, and `CONTEXT.md`, updating only relevant project-brain files and asking before breaking changes.
- `grill-me` now explicitly forbids reflexive praise and requires skeptical challenge before approving an idea
- Per-project memory directory renamed from `.claude/brain/` to `.claude/memory/` to align with pratique-ia standard
- `config/brain-templates/` renamed to `config/memory-templates/`
- `.claude/CLAUDE.md` VSCode fallback simplified to `@../AGENTS.md` (AGENTS.md contains memory @-imports)
- AGENTS.md template now includes `## Memory` and `## Standards` sections with commented @-imports

### Migration
- Run `ai-dotfiles upgrade <project-path>` or `upgrade --all` on existing projects to auto-migrate `.claude/brain/` → `.claude/memory/`

### Added
- `ai-dotfiles merge-memory <path|--all>` — new CLI subcommand that backfills OKF-style `type:` / `updated:` frontmatter and any missing `## sections` from current templates into existing project memory files, without adding new files or changing content (uses `scripts/merge-memory.sh` + `scripts/merge-memory-md.py`)
- `scripts/merge-memory.sh` — focused backfill script; wraps `merge-memory-md.py` for a full project or all registered projects

### Fixed
- `brain-audit/scripts/audit.sh`: phases now skip gracefully when `compile.sh`, `connect.sh`, or `qa.sh` are absent instead of exiting with an error — allows the orchestrator to run with only the implemented phase scripts
- QMD embed/update failures in `brain-sync` now logged to `~/.claude/logs/brain-sync.log` instead of silenced with `2>/dev/null`

### Fixed (prior unreleased)
- **`brain-session-end.sh`**: removed broken `systemMessage` emission. `SessionEnd` hooks do NOT give Claude a final turn — that is `Stop` hook behavior. The message was emitted but never received. Replaced with a log-only warning written after sync (so `tail -30` in SessionStart catches it).
- **`brain-session-start.sh`**: `tail -20` → `tail -30` to ensure the 4-line missing-notes warning is visible (sync output is 23 lines; previous window cut the warning entirely).

### Added (prior unreleased)
- **`skills/capture/SKILL.md`**: added full skill content to `skills/` directory so Claude Code discovers `/capture` as a user-invocable skill. Previously the skill was only in the plugin marketplace stub and cache, not in the discoverable `skills/` tree.
- **`/capture` skill** (`capture@ldom1-ai-dotfiles`): new user-invocable skill that runs the full end-of-session workflow — write implementation notes, check pitfalls/lessons, run `sync.sh end`, prompt user to close. This is the primary path for session documentation; the SessionEnd hook is now a fallback only. (Renamed from `/exit` then `/wrap` — both are reserved or conflict-prone names.)

### Changed (prior unreleased)
- **SessionEnd implementation note enforcement**: `brain-session-end.sh` now scans `$BRAIN_PATH/inbox/daily/implementation/` for today's notes before syncing. Fallback warning is appended to the end-session log (shown in `LAST EXIT` at next `SessionStart`).

### Removed
- `clawvis-skills` MCP reference (pointed to non-existent file)
- `skills/brain-audit/scripts/compile.sh`, `connect.sh`, `qa.sh` (logic moved to SKILL.md)
- `skills/brain-audit/.claude-plugin/plugin.json` (replaced by root `plugin.json`)

## [0.2.0] - 2026-05-20

### Added

- **Per-project MCP wiring**: `ai-dotfiles init` and `ai-dotfiles upgrade` now configure both `code-index-mcp` (AST code search) and `qmd` (semantic vault search) in `<project>/.claude/settings.json`. Only brain-initialized projects get these MCPs.
- **Central QMD database**: vault indexed at `${HOME}/vault-qmd/index.sqlite` (controlled via `QMD_INDEX_PATH` in `brain.env`). One collection: `brain → $BRAIN_PATH`. Embeddings refresh automatically at session end via `brain-sync`.
- `config/brain-templates/mcp-settings.json.tpl` — MCP config template with `__PROJECT_PATH__` and `__QMD_INDEX_PATH__` placeholders; excluded from brain template copy.
- `scripts/lib-mcp.sh` — idempotent MCP config injection helper sourced by init + upgrade scripts.
- `brain-sync` end hook now runs `qmd update` (re-index new/changed files) then `qmd embed` after vault push (non-blocking; skipped if qmd not installed or `QMD_INDEX_PATH` unset).
- `brain.env` now exports `BRAIN_PATH` and `QMD_INDEX_PATH` so hooks and child processes inherit them without re-sourcing.
- **`brain-search` skill**: semantic/keyword vault search via qmd. Claude invokes it mid-session to retrieve past decisions, specs, lessons learned, or any vault knowledge relevant to the current task.

### Prerequisites (new)
- `jq` — `apt install jq` / `brew install jq`
- `uvx` — `pip install uv`
- `qmd` — `npm install -g @tobilu/qmd` (one-time vault setup required, see README)

- **Project Brain Sync**: per-project persistent knowledge layer synced bidirectionally between `<project>/.claude/brain/` and `$BRAIN_PATH/projects/<slug>/`.
  - `ai-dotfiles init <path>` — creates `.claude/brain/` with template files, mirrors to vault, registers in `config/brain-projects.tsv`
  - `ai-dotfiles upgrade <path|--all>` — adds missing template files without overwriting existing content
  - `ai-dotfiles sync <path|--all>` — manual bidirectional rsync (mtime wins via `rsync --update`)
  - Template files: `settings.json`, `OBJECTIVES.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `CONTEXT.md`, `ROADMAP.md`, `API.md` under `config/brain-templates/`
  - `brain-sync` start/end hooks now auto-sync all registered projects (vault→project on start, project→vault on end)
  - `brain-load` now detects `.claude/brain/settings.json` and injects `read_on_session_start` files (default: OBJECTIVES.md, CONTEXT.md) into session context
  - CLI entry point: `bin/ai-dotfiles` (symlinked to `~/.local/bin/` by `install.sh`)
  - Registry: `config/brain-projects.tsv` (header-only on fresh install; append-only from scripts)

- **Versioned Git hooks**: `git-hooks/pre-commit` (same behavior as local `.git/hooks/pre-commit`: block commits under `.cursor/plans|projects|plugins|skills-cursor` except tracked `.gitignore`, secret scan on staged diffs). `scripts/install.sh` sets `core.hooksPath` to `git-hooks`; `scripts/install-git-hooks.sh` does only that for fresh clones. `core.hooksPath` is per-clone local config — not stored in commits — so each machine runs install once.
- **Custom Claude Code statusline** (`.claude/statusline.py`) replacing `ccstatusline@latest`. Three lines: model + project + git branch (with dirty marker) · context compaction progress bar (`[████░░░░░░] NN%`) + `tok used` + cost · session % / reset + weekly % + `resets Fri … (N days)` (via cached `ccusage blocks`/`daily --json`). `CLAUDE_WEEKLY_LIMIT_TOK` defaults to 100M (Max-style); set `5000000` for Pro-style caps. Also `COMPACT_PCT`, `CTX_WINDOW`, `CCUSAGE_TOKEN_LIMIT`, `STATUSLINE_CACHE_TTL`. Wired into `.claude/settings.json`, `.claude/settings.json.tpl`, and `scripts/install.sh`.
- **Statusline fixes**: session `%` now defaults to current usage from `totalTokens/limit` without forcing `--token-limit max` (uses `CCUSAGE_TOKEN_LIMIT` only when explicitly set), and `.claude/statusline.py --debug` now prints a JSON diagnostic block with chosen session/week sources and raw denominators.

- **finops-audit**: JSON export capability with `--json`, `--both`, `--quiet` flags
  - Structured JSON reports with token aggregates (year/month/week/day)
  - Project and session-level breakdown
  - Configurable output path via `.claude/settings.json`
  - Backward compatible with existing markdown reports
  - Support for external tool integration (e.g., techspend visualizer)

- **Cursor rule** `.cursor/rules/graphify-context.mdc`: when `graphify-out*` exists at the project root (file or `graphify-out/` with `graph.json`), treat it as canonical architecture context; do not overwrite those artifacts.
- **CLAUDE.md**: same Graphify `graphify-out*` context rules plus existing `/graphify` skill trigger, under `## Graphify`.
- **graphify skill**: moved from `.claude/skills/graphify/` to `skills/graphify/`; `.claude/skills/graphify` and `.vibe/skills/graphify` are symlinks (same pattern as other skills). Cursor picks it up via `.cursor/skills` → `../skills`. Added `skills/graphify/.claude-plugin/plugin.json`, nested `skills/graphify/skills/graphify/SKILL.md` symlink, and marketplace entry.
- **graphify skill**: removed hardcoded uv clone path; resolve `GRAPHIFY_PROJECT` via env, `config/graphify.env`, `graphify-out/.graphify_project`, or **ask the user once** for the clone root. Added `config/graphify.env.example`, gitignore + `install.sh` bootstrap for `config/graphify.env`.

- **brain-route skill**: Session mode decision router that determines whether to run maintenance (brain-audit) or normal context load (brain-load) based on vault state
  - Decision rules: >7 days since last maintenance, >50 unprocessed raw files, or explicit --maintenance flag
  - Logs decision + reason to session context
  
- **brain-audit skill**: Comprehensive four-phase maintenance pipeline for Local Brain vault
  - **Phase 1**: Raw data compilation (raw → drafts → archive)
  - **Phase 2**: Connection detection (find orphaned notes, suggest semantic links)
  - **Phase 3**: Templated Q&A (run saved queries, auto-file results)
  - **Phase 4**: Digest generation + maintenance clock reset
  - All results appear in /inbox/ for human review + approval

- **Inbox/Journaling workflow**: New directory structure
  - `/inbox/drafts/` — raw data compiled into wiki articles (pending approval)
  - `/inbox/connections/` — suggested semantic links (pending approval)
  - `/inbox/qa/` — auto-filed query results (pending approval)
  - `/meta/last-maintenance.md` — tracks maintenance timestamp (7-day clock)
  - `/meta/queries/` — templated Q&A queries for automated synthesis

- **Integration**: brain-route wired into brain-sync session flow
  - brain-sync pull → brain-route decision → brain-audit OR brain-load
  - Seamless session start with no user configuration needed

### Removed

- **`notion-brain-sync` skill**: removed (`skills/notion-brain-sync/`). Notion ingest is no longer part of the standard workflow.
- **`token-watch` skill**: removed (`skills/token-watch/`).
- **`token-guard` skill**: removed (`skills/token-guard/`).

### Changed

- **Wiki source of truth**: switched from `docs/wiki/` stubs to direct `.wiki/` repository workflow. `scripts/update-wiki.sh` now commits/pushes local `.wiki/` changes.
- **CI**: removed dedicated wiki publish job from `ci.yml`; wiki updates are now explicit/manual via `scripts/update-wiki.sh` when needed.
- **Cleanup**: removed `docs/wiki/`, `.pre-commit-config.yaml`, and `requirements-dev.txt` from the wiki workflow path.
- **README**: Skills table updated; wiki process now points to local `.wiki/` + `scripts/update-wiki.sh`.
- **brain-sync**: Now calls brain-route after successful pull to determine session mode
- **brain-route / brain-audit**: ShellCheck clean — `SC1090`/`SC2155`/`SC2034` fixes in `_brain_env.sh`, `route.sh`, and `connect.sh`
- **finops-audit**: removed unused local variables in `skills/finops-audit/scripts/finops-audit.sh` to resolve ShellCheck `SC2034`.

## 2026-04-09

### Added
- New `server-audit` skill at `skills/server-audit/`.
- Robust audit script at `skills/server-audit/scripts/audit.sh` for local or SSH targets.
- Marketplace metadata for `server-audit` in `skills/server-audit/.claude-plugin/plugin.json`.
- Marketplace skill symlink at `skills/server-audit/skills/server-audit/SKILL.md -> ../../SKILL.md`.

### Changed
- `.claude/skills/*` now includes symlinks for all current repo skills, including `server-audit`.
- `.cursor/skills` symlink now points to shared `skills/`.
- `.claudeignore` now explicitly keeps `skills/`, `.claude/skills/`, and `.cursor/skills/` includable.
- `.gitignore` updated to version `.claude/settings.json` (while generation from `.claude/settings.json.tpl` is still supported).
- `.claude/settings.json` includes a `pre-commit` hook that blocks staged `.cursor` / `.vs` IDE files.
- `.gitignore` now ignores `.claude/logs/` and `.claude/usage-data/` runtime artifacts.
- `.claude/CLAUDE.md` adds operational guidance for remote-server verification and git hygiene.
- `server-audit` is upgraded to a config-driven parallel audit workflow with six dedicated check scripts and JSON aggregation.
- `.gitignore` now ignores `skills/server-audit/config/targets.json` and `skills/server-audit/out/` local runtime artifacts.
- Added documentation hygiene rules in both `.claude/CLAUDE.md` and `.cursor/rules/docs-hygiene.mdc`.
- `server-audit` now supports interactive startup prompts to choose checks/targets first, making the skill generic for marketplace users.
