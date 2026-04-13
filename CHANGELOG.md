# Changelog

## [Unreleased]

### Added

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

### Changed

- **Wiki source of truth**: switched from `docs/wiki/` stubs to direct `.wiki/` repository workflow. `scripts/update-wiki.sh` now commits/pushes local `.wiki/` changes.
- **CI**: removed dedicated wiki publish job from `ci.yml`; wiki updates are now explicit/manual via `scripts/update-wiki.sh` when needed.
- **Cleanup**: removed `docs/wiki/`, `.pre-commit-config.yaml`, and `requirements-dev.txt` from the wiki workflow path.
- **README**: Skills table lists all 11 repo skills with wiki URLs under `wiki/Skills/…`; FinOps + token plugins added to install snippet; wiki process now points to local `.wiki/` + `scripts/update-wiki.sh`.
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
