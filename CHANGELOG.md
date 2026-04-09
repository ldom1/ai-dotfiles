# Changelog

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
