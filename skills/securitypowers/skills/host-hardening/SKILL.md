---
name: host-hardening
description: Audit a deployed Linux host's hardening, read-only, against the profile's baseline (ANSSI BP-028 or CIS) with OpenSCAP and Lynis over SSH, then turn each failed rule into an Ansible change for the IaC repo. Use when the user asks "is my server hardened", "ANSSI audit", "CIS benchmark", "check the bare-metal node", "harden the host", or after a deployment.
---

# Host hardening audit

A technical audit, **not a certification**. Results depend on the installed SCAP content, its version and which rules apply to the host. Never write "compliant".

## Preconditions (all required)

1. `bash <plugin>/scripts/profile-check.sh <project>` prints `ok`.
2. The host appears in `authorized_targets` with scope `host-hardening`. Apply the target rules of `exposure-scan` § "Target rules" (literal name, pinned IP).
3. Show the owner: host, SSH alias, commands to run, files written under `/tmp`. **Ask for confirmation before the first SSH command.**
4. Read-only means: no config change, no package change, except a tool install the owner approves for this run. Output goes under `/tmp/sp-*` on the host, is copied back, then removed.
5. Passwordless sudo: `ssh <alias> 'sudo -n true'`. If it fails, give the owner the exact commands to run with `!` and read their output.

## OpenSCAP

1. Check the tools: `ssh <alias> 'rpm -q openscap-scanner scap-security-guide'`. If missing, ask the owner before `sudo dnf install -y openscap-scanner scap-security-guide`. Never install without a yes for this run.
2. Find the content: `ssh <alias> 'ls /usr/share/xml/scap/ssg/content/ssg-*-ds.xml'`.
3. **Check the profile exists**: `ssh <alias> 'oscap info --profiles <ds.xml>'`. Look for the profile matching `baseline` (e.g. `xccdf_org.ssgproject.content_profile_anssi_bp28_intermediary`). If it is missing, stop and say which profiles exist. Never assume a profile id.
4. Run:
   `ssh <alias> 'sudo oscap xccdf eval --profile <id> --results /tmp/sp-oscap.xml --report /tmp/sp-oscap.html <ds.xml>'`
   Exit 2 means "some rules failed", not an error. Exit 1 is an error.
5. Copy back with `scp`, then `ssh <alias> 'sudo rm -f /tmp/sp-oscap.xml /tmp/sp-oscap.html'`.
6. Count `rule-result/result` values in the XML: `pass`, `fail`, `notapplicable`, `notchecked`, `error`, `unknown`, `informational`. Report every count, plus the profile id, the `scap-security-guide` version and the `oscap --version`.
7. Fixes: `oscap xccdf generate fix --fix-type ansible --result-id "" --output <raw>/oscap-fix.yml <raw>/sp-oscap.xml` (locally or on the host). Never run the playbook on the host. Propose the relevant tasks as a change to the project's IaC repo.

## Lynis

1. Get a Lynis release locally (`git clone --depth 1 --branch <tag> https://github.com/CISOfy/lynis`). Print the tag. No EPEL, no install on the host.
2. `tar czf` it, `scp` to `/tmp/sp-lynis.tgz`, extract to `/tmp/sp-lynis/`, `sudo chown -R 0:0 /tmp/sp-lynis` (Lynis refuses files not owned by root when run as root).
3. `ssh <alias> 'cd /tmp/sp-lynis && sudo ./lynis audit system --quick --no-colors --logfile /tmp/sp-lynis.log --report-file /tmp/sp-lynis.dat'`
4. Copy back `/tmp/sp-lynis.dat`, then remove `/tmp/sp-lynis*` on the host.
5. Report `hardening_index`, every `warning[]` and the `suggestion[]` lines relevant to the profile's assets.

## Triage

- A failed rule that the profile accepts as a risk → `accepted`, with the profile row.
- `notchecked` and `error` are gaps in the audit, not passes. List them under "not verified".
- Rank fails by exposure: a fail on a public-facing service (sshd, Apache) outranks one on an unused subsystem.

## Output

For `audit-report`: profile id and versions, counts per result, the failed rules ranked, the Lynis index and warnings, and the Ansible changes proposed.
