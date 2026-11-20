---
name: iac-scan
description: Scan infrastructure as code — Ansible roles and playbooks, Dockerfiles, docker-compose, Kubernetes, Terraform, CI pipelines — for insecure configuration with Trivy, KICS and ansible-lint, and propose fixes as code changes. Use when a change touches Ansible, Docker, CI or deployment config, or when the user asks "is my Ansible secure", "scan my IaC", "check my Dockerfile", "audit the deployment repo".
---

# IaC scan

Finds insecure configuration **before** it reaches a host. Fixes stay in the IaC repo.

## Preconditions

1. `bash <plugin>/scripts/profile-check.sh <project>` prints `ok`.
2. Tools: `command -v trivy kics ansible-lint`. A missing one runs from its official image (pin the tag and print it in the report):
   - `docker run --rm -v "$PWD:/src" aquasec/trivy:<tag> config /src`
   - `docker run --rm -v "$PWD:/path" checkmarx/kics:<tag> scan -p /path -o /path/.agents/security-reports/raw/kics --disable-full-descriptions`
   - `uvx ansible-lint` (no global install).

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

Propose each fix as a diff in the IaC repo. Re-run the tool that found it. Run the repo's own check (`molecule test`, `ansible-playbook --check`, `docker build`) when one exists. Ask before any commit.

## Output

For `audit-report`: tool, rule id, file:line, severity after triage, status, tool versions.
