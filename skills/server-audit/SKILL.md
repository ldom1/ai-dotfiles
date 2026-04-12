---
name: server-audit
description: >-
  Run a comprehensive infra audit with parallel checks and structured JSON reporting.
  Use whenever the user asks to check server health, debug infra issues, audit Docker
  containers, nginx, Tailscale, Authelia, cron jobs, or git repos on a remote or local
  machine. Trigger on: "is everything running?", "check my server", "something's broken
  on the vps", "audit my infra", or any request to inspect a live environment.
user-invocable: true
---

# server-audit

Run **`/server-audit`** for on-demand infrastructure triage across Docker, nginx, Tailscale, Authelia, cron, and git.

## Usage

```bash
# interactive mode (recommended for marketplace / generic usage)
bash ~/ai-dotfiles/skills/server-audit/scripts/audit.sh

# config-driven mode (repeatable automation)
bash ~/ai-dotfiles/skills/server-audit/scripts/audit.sh \
  ~/ai-dotfiles/skills/server-audit/config/targets.json
```

## Parallel checks

- `check_docker.sh` — container running + health status
- `check_nginx.sh` — proxy endpoint response checks + buffering directives
- `check_tailscale.sh` — node visibility/online peer connectivity
- `check_authelia.sh` — auth portal + protected endpoint flow checks
- `check_cron.sh` — expected jobs present + recent execution activity
- `check_git.sh` — dirty tree + embedded-repo/submodule warnings

Each check writes one JSON object. The parent orchestrator runs all checks concurrently and calls `aggregate.py` to compile the final report.

## Agent behavior

When executed by an agent runtime, start by asking what to test (checks, targets, endpoints, repos), run selected checks as parallel sub-agents/tasks, produce one JSON report per check, then compile a parent summary ranked by severity with concrete fix actions.

## Output contract

- Per-check JSON: `skills/server-audit/out/<timestamp>/checks/*.json`
- Aggregated report: `skills/server-audit/out/<timestamp>/report.json`
- Terminal summary:
  - severity counts
  - top severity-ranked issues
  - suggested fixes

## JSON schema (per check)

```json
{
  "check": "docker|nginx|tailscale|authelia|cron|git",
  "status": "pass|warn|error",
  "severity": "critical|high|medium|low|info",
  "findings": ["..."],
  "evidence": ["..."],
  "suggested_fixes": ["..."],
  "meta": {}
}
```
