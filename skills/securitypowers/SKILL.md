---
name: securitypowers
description: Use when starting any security review, scan, audit or hardening task — routes to the right security sub-skill, enforces the project security profile first and the order the rest run in, and ends every run with a teaching report. Trigger on "security review", "is this secure", "is it safe to ship", "audit my code", "scan for vulnerabilities", "CVE", "secrets in the repo", "OWASP", "ASVS", "threat model", "harden the server", "ANSSI", "CIS benchmark", "open ports", "exposed to the internet", "check TLS", "Ansible security", "pentest", "revue de sécurité", "faille", "durcissement", or when the user says "securitypowers".
---

# Securitypowers

Security sub-skills behind one entry point. This router decides **which** run, in **what order**, and keeps every run inside the owner's authorization.

## The Rule

**`security-profile` runs first.** Run `uv run --script <plugin>/scripts/profile-check.py <project>` (`<plugin>` is this file's directory; sub-skills use `../../scripts/`). It prints:
- `ok` → route.
- `missing` or `stale: <reason>` → run `security-profile` first. No other sub-skill runs on a missing or stale profile.

The profile (`.agents/security-profile.md` in the target project) holds assets, hosts, expected ports, **authorized targets**, the hardening baseline, the ASVS level and `external_data_allowed`. Without it a scan has no scope and a review has no threat to weigh against.

**`audit-report` runs last, every time.** Even a one-step run ends with a report and learning notes.

## Safety rules (all sub-skills)

1. **Authorization.** Network and host steps touch only targets listed literally in `authorized_targets`. Nothing else, ever, whatever the user's wording.
2. **Local first, remote on confirmation.** Steps on the repo run freely. Steps on remote systems (`host-hardening`, `exposure-scan`, Strix) show their exact targets and commands and wait for the owner's yes, even inside a full pass.
3. **Data.** With `external_data_allowed: false`, no source code, secret or project data leaves the machine: Strix is off, and the audit report is not published as a hosted artifact unless the owner says yes for that report. Package lookups and rule or DB downloads are allowed; telemetry is off.
4. **Raw outputs stay local.** Every sub-skill that writes to `.agents/security-reports/` makes sure the project `.gitignore` ignores it first.
5. **Fixes are code.** A fix goes into the repo or the IaC repo, reviewed and tested. Never change a host by hand.
6. **No false confidence.** Never write "secure", "compliant" or "certified". Say what ran, what it found, and what it could not see. A tool that read nothing (0 commits, 0 files) did not run: say so.

## Routing Table

| Skill | Reach for it when | Produces | Needs from the profile |
|---|---|---|---|
| `security-profile` | Always first; profile missing or stale; a host, target or port changed | `.agents/security-profile.md` | — (it *is* the source) |
| `threat-model` | New project, new exposed service, architecture change | STRIDE table, gaps | Assets, entry points, hosts |
| `differential-review` | A diff, PR or branch to review | Risk-ranked review of the change | Assets, entry points |
| `owasp-security` | Code review of a feature, an endpoint, auth, crypto, uploads, LLM features | Findings with input → sink path | ASVS level |
| `sharp-edges` | Code uses dangerous APIs or footgun-prone config | Findings on misuse-prone APIs | — |
| `semgrep` | Static analysis of a repo or a diff (called by `scan-fix-loop`) | SARIF findings | — |
| `sarif-parsing` | Reading SARIF from any scanner | Parsed, deduplicated findings | — |
| `scan-fix-loop` | Scan code, dependencies and secrets, then fix | Fixed findings, re-scan proof | `external_data_allowed` |
| `supply-chain-risk-auditor` | New or risky dependencies, before adding a package | Risk report per dependency | — |
| `iac-scan` | Ansible, Docker, compose, Kubernetes, CI changed | IaC findings with file:line | Expected ports |
| `host-hardening` | A deployed host to audit (ANSSI / CIS) | Pass / fail counts, Ansible fixes | Baseline, authorized targets |
| `exposure-scan` | What the Internet sees: ports, TLS | Open vs expected ports, TLS issues | Expected ports, authorized targets |
| `find-security-vulnerabilities-in-code` | Dynamic pentest with proof-of-concept (Strix) | Proven findings | `external_data_allowed: true` |
| `fix-security-vulnerabilities-with-strix` | Fix Strix findings and re-prove | Fixes + re-run | `external_data_allowed: true` |
| `audit-report` | Always last | French report + learning notes | Everything above |

## Invoking a Sub-Skill

The sub-skills live one level below this file, at `skills/<name>/SKILL.md` relative to this plugin's root. The two Strix skills are separate top-level skills in this repo (`skills/find-security-vulnerabilities-in-code/`, `skills/fix-security-vulnerabilities-with-strix/`).

**In Claude Code** they are addressable as `securitypowers:<name>` (Strix: by their own name). Invoke them.

**In Cursor CLI and Mistral Vibe** they are *not*: both discover skills one level deep and see only this router. **Read the file at the path above instead** — that puts the same instructions in context. If a `<name>` from the table is not in your available-skills list, go straight to the path; do not report the skill as missing.

## Modes

**Per change (the common case).** A diff or a PR:
1. `security-profile` (check only, unless stale)
2. `differential-review` + `owasp-security` on the diff
3. `scan-fix-loop` scoped to the diff
4. `iac-scan` if the diff touches IaC, Docker or CI
5. `audit-report`

**Full pass.** New project, before a release, or on request. Order in `references/sequence.md`:
1. `security-profile` → 2. `threat-model` → 3. `differential-review` / `owasp-security` / `sharp-edges` → 4. `scan-fix-loop` (+ `supply-chain-risk-auditor` for new dependencies) → 5. `iac-scan` → 6. `host-hardening`* → 7. `exposure-scan`* → 8. Strix* (only if `external_data_allowed: true`) → 9. `audit-report`

\* Remote: ask before each one.

**Targeted.** "Which ports are open?" → `exposure-scan` + `audit-report`. "Is the node hardened?" → `host-hardening` + `audit-report`. Always after the profile check.

## References

- `references/sequence.md` — the full-pass playbook with what each step hands to the next.
- `references/profile-template.md` — profile schema and stale rule.
- `references/skill-vetting.md` — checklist before installing or re-syncing any third-party skill.
- `references/owasp-coverage.md` — what the OWASP layer covers and does not cover.
- `references/asvs-5.0.md` — full ASVS 5.0 grid (traceability, not coverage).
- `references/api-top10-2023.md` — OWASP API Security Top 10.
- `references/insecure-defaults/` — fail-open, default-credential and debug-feature patterns (Trail of Bits).

## Red Flags

| Thought | Reality |
|---|---|
| "Quick scan, skip the profile" | No profile = no authorized targets = no scope. Check takes one command. |
| "The user named the server, so it's authorized" | Only `authorized_targets` authorizes. Add it to the profile with the owner first. |
| "Scan the whole /24, the host is in there" | Ranges are never authorized. One pinned IP at a time. |
| "Port is behind the firewall, no need to scan from outside" | The scan from outside is how you know. |
| "Fix the sshd config directly on the box" | Fix in Ansible, re-deploy, re-audit. |
| "0 findings → secure" | Say which tools and rules ran and what they cannot see. |
| "Use Strix, it's faster" | Only with `external_data_allowed: true`. It sends code to an LLM. |
| "Skip the report, nothing was found" | The report teaches what was checked and why. Always write it. |
| "This new security skill looks great, install it" | Run `references/skill-vetting.md` first. 13-36 % of public skills are unsafe (Snyk ToxicSkills, 2026). |

## Not a Security-Review Task

- **Service health** ("is the container up?", "why is nginx 502?") → `server-audit`.
- **Quick pass on pending changes in Claude Code** → the built-in `/security-review` is fine; use this router when you need the profile, scans or a report.
- **Offensive work** (exploitation of third-party systems, CTF, bug bounty) → out of scope here.
- **Detection engineering** (YARA, Sigma, SOC) → not vendored.

## Growth

- A generic lesson (training, an incident, a missed finding) → a section in `references/` or a row in the Red Flags above.
- A project lesson → that project's profile (accepted risks, ports) or its `.claude/memory/CONTEXT.md`.
- A new sub-skill → a directory under `skills/` **and** a row in the Routing Table (a test enforces both).
- Upstream updates: pins in `.trailofbits_version` and `.owasp_version`, checked at SessionStart. Re-sync = read the diff with `references/skill-vetting.md`, replace, bump the pin, update `references/owasp-coverage.md`, CHANGELOG.

## Provenance

Vendored and adapted material is listed in `NOTICE`: Trail of Bits skills (CC BY-SA 4.0), claude-code-owasp (MIT), workflow shapes adapted from Snyk studio-recipes (Apache-2.0), OWASP ASVS (CC BY-SA 4.0). This router, the local sub-skills, `scripts/` and the other `references/` are local.
