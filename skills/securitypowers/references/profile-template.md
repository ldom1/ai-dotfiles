# Security profile template

The `security-profile` sub-skill writes this file to `.agents/security-profile.md` in the **target project**. Every other securitypowers sub-skill reads it first.

Rules:
- The file is a snapshot. Rewrite it in place. Never add a history or a dated section.
- No secrets: no passwords, keys, tokens or vault content. Name the SSH alias, not the key.
- `sources:` lists the repo files the draft was built from (inventory, firewall rules, compose files, web server config). Paths are relative to the project root.
- After an edit, set `reviewed:` to today and recompute `sources_sha256` with `scripts/profile-check.sh --hash <project>`.

## Stale rule

`scripts/profile-check.sh <project>` prints `ok`, `missing` or `stale: <reason>`. The profile is stale when:
- `reviewed` is more than 90 days old (`PROFILE_MAX_AGE_DAYS`);
- a file in `sources:` changed or is missing;
- the owner says that a host, an authorized target or a port changed (the script cannot see this: ask).

## Template

```markdown
---
reviewed: YYYY-MM-DD
sources:
  - inventory/prod/hosts.yml
  - roles/firewall/defaults/main.yml
sources_sha256: <output of profile-check.sh --hash>
baseline: anssi_bp28_intermediary   # anssi_bp28_minimal|intermediary|enhanced|high, cis_l1, cis_l2, none
asvs_level: L2                       # L1 | L2 | L3
external_data_allowed: false         # true lets code or project data reach an external service (Strix LLM, cloud scanner)
---

# Security profile — <project>

## Assets
What an attacker wants, and how sensitive it is.

| Asset | Sensitivity | Where it lives |
|---|---|---|
| Customer simulation data | High (contractual, sovereign) | /data on node1 |

## Deployment
| Host | OS | Role | Reach (SSH alias) |
|---|---|---|---|
| node1 | AlmaLinux 9 | controller + compute + login + web | `hpc-dev` |

## Expected ports
One row per listening port. `exposure-scan` flags every open port that is not here.

| Host | Port/proto | Interface | Service | Why it is open |
|---|---|---|---|---|
| node1 | 443/tcp | public | Apache (Open OnDemand) | user portal |
| node1 | 22/tcp | public | sshd | admin + login node |
| node1 | 6817/tcp | private | slurmctld | cluster only |

## Authorized targets
Exact host names or IPs the owner may scan. No ranges, no wildcards. Pin the IP of each name.

| Target | Pinned IP | Authorized by | Scope |
|---|---|---|---|
| hpc-dev.example.com | 203.0.113.10 | owner, written OK on YYYY-MM-DD | exposure-scan, host-hardening |

## Entry points
Where untrusted data enters: web routes, uploads, SSH, job scripts, APIs, webhooks.

## Accepted risks
| Finding | Reason | Owner | Review by |
|---|---|---|---|
```
