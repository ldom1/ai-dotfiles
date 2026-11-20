---
name: security-profile
description: Write or refresh a project's security profile (.agents/security-profile.md) — assets, hosts, expected open ports, authorized scan targets, hardening baseline (ANSSI BP-028 or CIS), ASVS level, external data policy, accepted risks. Always the first step of securitypowers. Use when the profile is missing or stale, or when the user says "security profile", "set up security context", "which ports should be open", "what may I scan".
---

# Security profile

Writes `.agents/security-profile.md` in the target project. Every other securitypowers sub-skill reads it. Without it they refuse to run.

Schema and stale rule: `../../references/profile-template.md` (relative to this file). Read it first.

## Steps

1. **Check.** Run `uv run --script ../../scripts/profile-check.py <project>` (path relative to this file). `ok` → stop, unless the owner says a host, target or port changed.
2. **Auto-draft from the repo.** Read only what describes the attack surface:
   - Ansible inventories, `group_vars`, firewall and SSH roles;
   - `docker-compose*.yml`, Dockerfiles, Kubernetes manifests;
   - web server config (Apache, nginx), reverse proxy, OIDC config;
   - README and architecture docs.
   List every file you used under `sources:`.
3. **Fill the tables.** Mark every value you inferred with `(inferred)`. Never invent an IP or a host name.
4. **Ask the owner, one question at a time,** for what the repo cannot tell:
   - `authorized_targets` — the owner must name them. Never infer a target.
   - `external_data_allowed` — default `false`. Employer code: `false` unless the owner confirms that the internal policy allows it.
   - `baseline` and `asvs_level`.
5. **Write.** Set `reviewed:` to today. Write the file. Then run `uv run --script ../../scripts/profile-check.py --hash <project>` and write its output to `sources_sha256`. Re-run the check: expect `ok`.
6. **Commit or not.** The profile has no secrets and is meant to be committed. It names hosts and ports: ask the owner before committing it to a public repo.

## Red flags

| Thought | Reality |
|---|---|
| "The domain is in the README, so it's an authorized target" | Only the owner authorizes a target. Ask. |
| "Port 3306 is open in compose, add it to expected ports" | Expected means intended. Ask why it is open; it may be the finding. |
| "I'll fill the profile later" | The other sub-skills refuse without it. It takes five minutes. |
