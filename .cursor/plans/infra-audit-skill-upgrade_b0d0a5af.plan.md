---
name: infra-audit-skill-upgrade
overview: Upgrade `server-audit` into a configurable, comprehensive infrastructure audit skill that runs parallel sub-checks, emits structured JSON per check, and compiles a severity-ranked summary; add persistent Claude/Cursor rules to enforce changelog and README updates when relevant.
todos:
  - id: config-schema
    content: Add `targets.json.example` schema and parser wiring in orchestrator
    status: completed
  - id: parallel-checks
    content: Implement 6 dedicated check scripts returning normalized JSON
    status: completed
  - id: aggregation
    content: Implement `aggregate.py` to compile severity-ranked report and fixes
    status: completed
  - id: skill-doc
    content: Update `SKILL.md` usage and JSON/report contract
    status: completed
  - id: rules
    content: Add Claude + Cursor docs hygiene rule for changelog/README updates
    status: completed
  - id: project-docs
    content: Update `README.md` and `CHANGELOG.md` for the new capability
    status: completed
isProject: false
---

# Infrastructure Audit Skill + Docs Rule Plan

## Scope
Implement a reusable on-demand audit workflow in `skills/server-audit` with:
- parallel sub-check execution for Docker/nginx/Tailscale/Authelia/cron/git checks
- per-check structured JSON outputs
- parent aggregation into severity-ranked summary + suggested fixes
- persistent documentation hygiene rule in both Claude and Cursor configs

## Files to Add/Update
- `skills/server-audit/SKILL.md` (upgrade instructions + execution contract)
- `skills/server-audit/scripts/audit.sh` (parent orchestrator)
- `skills/server-audit/scripts/check_docker.sh`
- `skills/server-audit/scripts/check_nginx.sh`
- `skills/server-audit/scripts/check_tailscale.sh`
- `skills/server-audit/scripts/check_authelia.sh`
- `skills/server-audit/scripts/check_cron.sh`
- `skills/server-audit/scripts/check_git.sh`
- `skills/server-audit/scripts/aggregate.py` (merge JSON + severity ranking + fix hints)
- `skills/server-audit/config/targets.json.example` (default config schema)
- `skills/server-audit/.claude-plugin/plugin.json` (confirm metadata still valid)
- `skills/server-audit/skills/server-audit/SKILL.md` (confirm symlink intact)
- `.claude/CLAUDE.md` (add docs update rule)
- `.cursor/rules/docs-hygiene.mdc` (always-apply rule)
- `README.md` (document new audit usage/config)
- `CHANGELOG.md` (record behavior/rule additions)

## Implementation Approach
1. Define a stable config contract in `targets.json`:
   - ssh target(s), nginx endpoints, tailscale peers, authelia endpoints, cron freshness thresholds, git repo paths.
   - default to JSON config file with optional CLI override for path.
2. Split each check into a focused script that returns one JSON object:
   - fields: `check`, `status`, `severity`, `findings[]`, `evidence[]`, `suggested_fixes[]`, `meta`.
3. Run checks in parallel from `audit.sh`:
   - launch sub-check scripts concurrently, collect exit codes/artifacts, avoid full-run failure on one check error.
4. Aggregate via `aggregate.py`:
   - merge per-check JSON files, normalize severities, rank issues, compute summary counts, and print:
     - `report.json` (machine-readable)
     - concise human summary block.
5. Update `SKILL.md` to instruct agent behavior:
   - explicitly require parallel sub-agents/checkers and JSON outputs.
   - include run commands for local/SSH config-driven audits.
6. Add persistent docs rule in both systems:
   - Claude: section requiring changelog update + README update when user-facing behavior/setup changes.
   - Cursor: new always-apply `.mdc` rule with same requirement.
7. Update docs:
   - README: config file format + expected report outputs + invocation examples.
   - CHANGELOG: entry for audit architecture + new docs hygiene rule.

## Output Contract (Audit)
- `skills/server-audit/out/<timestamp>/checks/*.json` (one file per check)
- `skills/server-audit/out/<timestamp>/report.json` (final merged report)
- terminal summary with severity totals and top fixes

## Validation
- Local smoke run with sample config
- Verify each check emits valid JSON even on command failures/timeouts
- Verify aggregator ranking order: `critical > high > medium > low > info`
- Verify marketplace-compatible symlink path remains correct
- Verify docs/rules mention changelog+README requirement consistently