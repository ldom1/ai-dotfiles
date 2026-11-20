---
name: iac-scan
description: Scan infrastructure as code — Ansible roles and playbooks, Dockerfiles, docker-compose, Kubernetes, Terraform, CI pipelines — for insecure configuration with Trivy, KICS and ansible-lint, and propose fixes as code changes. Use when a change touches Ansible, Docker, CI or deployment config, or when the user asks "is my Ansible secure", "scan my IaC", "check my Dockerfile", "audit the deployment repo".
---

# IaC scan

Finds insecure configuration **before** it reaches a host. Fixes stay in the IaC repo.

## Preconditions

1. `uv run --script ../../scripts/profile-check.py <project>` (path relative to this file) prints `ok`.
2. Tools: `command -v trivy kics ansible-lint`. A missing one runs from its official image (pin the tag and print it in the report):
   - `docker run --rm -v "$PWD:/src" aquasec/trivy:<tag> config /src`
   - `docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/path" checkmarx/kics:<tag> scan -p /path -o /path/.agents/security-reports/raw/<date>/kics --report-formats json --disable-full-descriptions`
   - `uvx ansible-lint` (no global install).
3. Before the first write, add `.agents/security-reports/` to the project `.gitignore` if the line is missing: raw outputs map the attack surface.

## Scans

Raw outputs go to `.agents/security-reports/raw/<date>/`.

| Target | Command |
|---|---|
| Dockerfiles, compose, Kubernetes, Terraform, Helm | `trivy config --format json --output <raw>/trivy-config.json <project>` |
| Ansible, plus a second opinion on the above | `kics scan -p <project> -o <raw>/kics --report-formats json --disable-full-descriptions` |
| Ansible style and risky modules | `ansible-lint --profile production --format json <playbook-or-dir> > <raw>/ansible-lint.json` |

Then read `../../references/insecure-defaults/*.md` (Trail of Bits corpus) and sweep the IaC by hand for:
- fallback secrets and default credentials in `defaults/`, `group_vars/`, templates;
- `no_log` missing on tasks that handle secrets;
- services bound to `0.0.0.0` that the profile lists as private;
- firewall rules wider than `expected_ports`;
- `validate_certs: false`, `StrictHostKeyChecking no`, `become` on tasks that do not need it;
- secrets outside `ansible-vault`.

## Triage

- Merge findings from the three tools. Drop duplicates (same file:line, same issue).
- Check each against the profile: a port open in IaC but missing from `expected_ports` is a finding, even if no tool flagged it.
- Severity by effect on the deployed host, not by the tool's label. Say why when you change it.

## Fix

Propose each fix as a diff in the IaC repo. Re-run the tool that found it. Run the repo's own **local** checks when they exist: `ansible-playbook --syntax-check`, `molecule test` (local VM or container), `docker build`. Never run `ansible-playbook --check` or any command that uses a real inventory: it connects to the hosts, and tasks with `check_mode: false` really run. Hosts are reached only through `host-hardening` and `exposure-scan`, after their target rules. Ask before any commit.

## Output

For `audit-report`: tool, rule id, file:line, severity after triage, status, tool versions.
