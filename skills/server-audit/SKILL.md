---
name: server-audit
description: >-
  Run a comprehensive infra audit with parallel checks and structured JSON reporting.
  Use whenever the user asks to check server health, debug infra issues, audit Docker
  containers, nginx/Traefik, Coolify, Tailscale, Authelia, cron/systemd-timers, systemd
  units, or git repos on a remote or local machine. Trigger on: "is everything running?",
  "check my server", "something's broken on the vps", "audit my infra", or any request
  to inspect a live environment.
user-invocable: true
---

# server-audit

Run **`/server-audit`** for on-demand infrastructure triage across Docker, network (nginx/Traefik), Coolify, Tailscale, Authelia, cron/systemd-timers, systemd units, and git.

## Agent behavior — always ask, never hardcode

**Never read or reuse a previously saved `config/targets.json` when invoked as an agent skill, and never hardcode a specific user's host/SSH details into this skill.** That file only exists for a human running the CLI directly in "repeatable automation" mode (see Usage below) — an agent must not treat it as a default.

Before running anything, ask the user which server to audit and how to reach it — e.g.:

> "Which server do you want to audit?"

The user's answer typically names the target and the SSH command in one line, e.g. *"Audit HP elite server, using ssh hp-elite-server"* — parse the SSH alias/host, user, and port straight out of that (falling back to `~/.ssh/config` for anything unstated: alias resolves to `HostName`/`User`/`Port`/`IdentityFile` there). Only ask a follow-up if the target is genuinely ambiguous (e.g. more than one plausible host, or no SSH info given at all).

Then also decide (or infer from context/conversation — e.g. from an Ansible inventory or prior discussion in the session — rather than re-prompting for things you can already see) which checks matter for this host: not every host runs Coolify or nginx, and the checks that don't apply skip gracefully, so default to running all of them unless the user narrows it down.

With the target and checks decided, **build a fresh JSON config in the scratchpad directory** (never in `skills/server-audit/config/`) matching the schema below, populated only with what this run needs, and invoke:

```bash
bash ~/ai-dotfiles/skills/server-audit/scripts/audit.sh /path/to/scratchpad/audit-config.json
```

Run the checks, produce one JSON report per check, then compile a parent summary ranked by severity with concrete fix actions. Discard the scratch config at the end of the task — it's per-run, not a persisted target.

## Usage (human/CLI, not agent mode)

```bash
# interactive mode (recommended for marketplace / generic usage)
bash ~/ai-dotfiles/skills/server-audit/scripts/audit.sh

# config-driven mode (repeatable automation — the human maintains config/targets.json themselves)
bash ~/ai-dotfiles/skills/server-audit/scripts/audit.sh \
  ~/ai-dotfiles/skills/server-audit/config/targets.json
```

## Parallel checks

- `check_docker.sh` — container running + health status
- `check_network.sh` — reverse proxy checks (nginx and/or Traefik — whichever is present; skips gracefully if either/both is absent) + endpoint reachability
- `check_coolify.sh` — Coolify control-plane container health (skips gracefully if Coolify isn't detected on the host)
- `check_tailscale.sh` — node visibility/online peer connectivity
- `check_authelia.sh` — auth portal + protected endpoint flow checks (redirect-aware, does not follow redirects when comparing status codes)
- `check_cron.sh` — expected jobs present (crontab or systemd timers) + recent execution activity
- `check_systemd.sh` — failed units + required services active
- `check_git.sh` — dirty tree + embedded-repo/submodule warnings

Each check writes one JSON object. The parent orchestrator runs all checks concurrently and calls `aggregate.py` to compile the final report.

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
  "check": "docker|network|coolify|tailscale|authelia|cron|systemd|git",
  "status": "pass|warn|error",
  "severity": "critical|high|medium|low|info",
  "findings": ["..."],
  "evidence": ["..."],
  "suggested_fixes": ["..."],
  "meta": {}
}
```

## Config schema

See `config/targets.json.example` for the full shape. Key sections an agent typically fills from the conversation:

```json
{
  "ssh": { "user": "...", "host": "...", "port": 22 },
  "docker": { "target": "remote", "required_containers": [], "health_required": true },
  "network": { "target": "remote", "traefik_container": "", "test_endpoints": [], "require_buffering_directives": [] },
  "coolify": { "target": "remote", "required_containers": [], "health_url": "" },
  "tailscale": { "target": "remote", "peer_hosts": [] },
  "authelia": { "target": "local", "portal_url": "", "protected_url": "", "expect_redirect_when_unauthenticated": true },
  "cron": { "target": "remote", "required_patterns": [], "max_age_hours": 24 },
  "systemd": { "target": "remote", "required_services": [] },
  "git": { "target": "local", "repo_paths": [] }
}
```
