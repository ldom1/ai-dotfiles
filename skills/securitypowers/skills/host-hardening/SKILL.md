---
name: host-hardening
description: Audit a deployed Linux host's hardening, read-only, against the profile's baseline (ANSSI BP-028 or CIS) with OpenSCAP and Lynis over SSH, then turn each failed rule into an Ansible change for the IaC repo. Use when the user asks "is my server hardened", "ANSSI audit", "CIS benchmark", "check the bare-metal node", "harden the host", or after a deployment.
---

# Host hardening audit

A technical audit, **not a certification**. Results depend on the installed SCAP content, its version and which rules apply to the host. Never write "compliant".

## Preconditions (all required)

1. `uv run --script ../../scripts/profile-check.py <project>` (path relative to this file) prints `ok`.
2. The host appears in `authorized_targets` with scope `host-hardening`. Apply the target rules of `exposure-scan` § "Target rules" (literal name, pinned IPs).
3. **Tie the SSH alias to the target.** `ssh -G <alias> | awk '$1=="hostname"{print $2}'` must print the authorized name or one of its pinned IPs. Show the owner any `proxyjump` line from `ssh -G <alias>`. A mismatch (stale alias, other host): stop.
4. Show the owner: host, SSH alias, the commands below, the temp directory. **Ask for confirmation before the first SSH command.**
5. Read-only means: no config change, no package change, except a tool install the owner approves for this run.
6. Passwordless sudo: `ssh <alias> 'sudo -n true'`. If it fails, give the owner the exact commands to run with `!` and read their output.
7. Before the first write, add `.agents/security-reports/` to the project `.gitignore` if the line is missing: raw outputs map the attack surface.

## Work directory on the host

The host may be a multi-user login node: a fixed name under `/tmp` lets a local user plant files that then run as root. Use a root-owned directory created for this run only:

```bash
D=$(ssh <alias> 'sudo mktemp -d /root/sp.XXXXXX')   # root-owned, mode 0700
```

Every file below goes under `$D`. Copy results back with `ssh <alias> "sudo cat $D/<file>" > <raw>/<file>` (the files are root-only). At the end: `ssh <alias> "sudo rm -rf $D"`, then check it is gone (`sudo test ! -e $D`).

## OpenSCAP

1. Check the tools: `ssh <alias> 'rpm -q openscap-scanner scap-security-guide'`. If missing, ask the owner before `sudo dnf install -y openscap-scanner scap-security-guide`. Never install without a yes for this run.
2. Find the content: `ssh <alias> 'ls /usr/share/xml/scap/ssg/content/ssg-*-ds.xml'`.
3. **Check the profile exists**: `ssh <alias> 'oscap info --profiles <ds.xml>'`. The profile id is `xccdf_org.ssgproject.content_profile_<baseline>` (e.g. `anssi_bp28_intermediary`, `cis_server_l1`). If it is missing, stop and say which profiles exist. Never assume a profile id.
4. Run:
   `ssh <alias> "sudo oscap xccdf eval --profile <id> --results $D/oscap.xml --report $D/oscap.html <ds.xml>"`
   Exit 2 means "some rules failed", not an error. Exit 1 is an error.
5. Copy back `oscap.xml` and `oscap.html`.
6. Count `rule-result/result` values in the XML: `pass`, `fail`, `notapplicable`, `notchecked`, `error`, `unknown`, `informational`. Report every count, plus the profile id, the `scap-security-guide` version (`rpm -q`) and `oscap --version`.
7. Fixes: `oscap xccdf generate fix --fix-type ansible --result-id "" --output <raw>/oscap-fix.yml <raw>/oscap.xml` (locally or on the host). If oscap rejects the empty id, read the `TestResult id=` attribute in the XML and pass it. Never run the playbook on the host. Propose the relevant tasks as a change to the project's IaC repo.

## Lynis

1. Get a Lynis release locally (`git clone --depth 1 --branch <tag> https://github.com/CISOfy/lynis`). Print the tag. No EPEL, no install on the host.
2. Stream it into the root-owned directory, so no user-writable copy exists:
   `tar czf - -C <local-clone-parent> lynis | ssh <alias> "sudo tar xzf - -C $D && sudo chown -R 0:0 $D/lynis"`
3. `ssh <alias> "cd $D/lynis && sudo ./lynis audit system --quick --no-colors --logfile $D/lynis.log --report-file $D/lynis.dat"`
4. Copy back `lynis.dat`.
5. Report `hardening_index`, every `warning[]` and the `suggestion[]` lines relevant to the profile's assets.

## Triage

- A failed rule that the profile accepts as a risk → `accepted`, with the profile row.
- `notchecked` and `error` are gaps in the audit, not passes. List them under "not verified".
- Rank fails by exposure: a fail on a public-facing service (sshd, Apache) outranks one on an unused subsystem.

## Output

For `audit-report`: profile id and versions, counts per result, the failed rules ranked, the Lynis index and warnings, and the Ansible changes proposed.
