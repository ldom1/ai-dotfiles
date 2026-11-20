# Full-pass sequence

The ordered playbook for a full security pass. Each step names what it needs and what it hands on. Steps 6-8 act on remote systems: show targets and commands, then wait for the owner's yes.

| # | Step | Needs | Hands on | Skip when |
|---|---|---|---|---|
| 1 | `security-profile` | Repo files, owner answers | `.agents/security-profile.md` (`ok`) | Never |
| 2 | `threat-model` | Profile | Ranked threats, gaps to check | Profile and architecture unchanged since the last model |
| 3 | `differential-review` / `owasp-security` / `sharp-edges` | Profile, threats | Review findings | No code in scope (IaC-only repo: go to 5) |
| 4 | `scan-fix-loop` (+ `supply-chain-risk-auditor` for new deps) | Profile | Fixed findings, re-scan proof | No code and no lockfile |
| 5 | `iac-scan` | Profile (expected ports) | IaC findings, firewall diffs | No IaC, Docker or CI |
| 6 | `host-hardening` (remote) | Profile (baseline, authorized targets), SSH access | Pass / fail counts, Ansible fixes | No deployed host, or owner says no |
| 7 | `exposure-scan` (remote) | Profile (expected ports, authorized targets), outside machine | Open vs expected ports, TLS issues | No Internet-facing host, or owner says no |
| 8 | Strix (remote, LLM) | `external_data_allowed: true`, running app | Proven findings | `external_data_allowed: false` |
| 9 | `audit-report` | Everything above | Report + learning notes | Never |

## Why this order

- The profile first: it decides scope and authorization for everything after it.
- The threat model before the review: the review then weighs findings against real threats instead of a generic list.
- Code before IaC before hosts: a fix in code or IaC is cheap; a finding on a host usually traces back to IaC, so step 5 explains step 6.
- Hardening before exposure: a service that hardening says is bound to `localhost` should not appear in the exposure scan; when it does, both results point at the same fix.
- The report last: it needs every step's result, including the ones that did not run.

## Per-change mode

Steps 1 (check only), 3 (on the diff), 4 (scoped), 5 (if IaC changed), 9.
