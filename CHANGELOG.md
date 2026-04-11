# Changelog

## [Unreleased]

### Added

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

- **brain-sync**: Now calls brain-route after successful pull to determine session mode

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
