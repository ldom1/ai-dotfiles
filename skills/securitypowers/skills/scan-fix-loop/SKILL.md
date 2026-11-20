---
name: scan-fix-loop
description: Scan a repo for vulnerable code, vulnerable dependencies and leaked secrets with open-source scanners (Semgrep CE, osv-scanner, gitleaks), then fix each confirmed issue, re-scan and run the tests — no Snyk account needed. Use when the user asks to "scan and fix", "fix vulnerabilities", "check dependencies for CVEs", "find secrets in the repo", "security scan this repo", or after a review found issues to remediate.
---

# Scan-fix loop

The workflow shape comes from Snyk's `snyk-fix` skill (snyk/studio-recipes, Apache-2.0, see `../../NOTICE`): scan → pick a target → fix every instance → re-scan → test → ask before any commit or PR. The scanners here are open source and need no account.

## Preconditions

1. `uv run --script ../../scripts/profile-check.py <project>` (path relative to this file) prints `ok`. Otherwise run `security-profile` first.
2. Read `external_data_allowed` in the profile. These scanners keep source code local in every case. Allowed outbound traffic: package name and version lookups (osv.dev), rule and DB downloads. Telemetry stays off.
3. Tools: check `command -v semgrep osv-scanner gitleaks`. A missing one runs from its official image (pin the tag you use and print it in the report):
   - `docker run --rm -v "$PWD:/src" ghcr.io/google/osv-scanner:<tag> scan source -r /src`
   - `docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/src:ro" -v "$PWD/<raw>:/out" ghcr.io/gitleaks/gitleaks:<tag> git /src --redact --report-format json --report-path /out/gitleaks-git.json`
     In a git worktree or a submodule the real `.git` is outside the mount: clone first (`git clone --no-local <project> <scratch>`) and scan the clone. Run as your own user: as root, git refuses the repo ("dubious ownership") and gitleaks scans nothing.
   - Semgrep: the `semgrep` sub-skill handles install and `--metrics=off`.
   Never install with `curl | bash`.

## Phase 1 — Scan

Write raw outputs to `.agents/security-reports/raw/<date>/`. Before the first write, add `.agents/security-reports/` to the project `.gitignore` if the line is missing: raw outputs map the attack surface.

| Scan | Command | Notes |
|---|---|---|
| Code (SAST) | Run the `semgrep` sub-skill (Trail of Bits) in "important only" mode, with output directory `<raw>/semgrep` | It shows the ruleset plan and asks before running. Without an explicit output directory it writes `./static_analysis_semgrep_N` at the repo root, where git can track it. Results: SARIF; read with `sarif-parsing`. |
| Dependencies (SCA) | `osv-scanner scan source -r <project> --format json --output <raw>/osv.json` | Exit 1 means vulnerabilities found, not a failure. |
| Secrets, history | `gitleaks git <project> --redact --report-format json --report-path <raw>/gitleaks-git.json` | **Always `--redact`**: a secret must never enter the conversation. Read the `N commits scanned` line: compare N with `git rev-list --count --all`. `0 commits` = the scan did not run. |
| Secrets, working tree | `gitleaks dir <project> --redact --report-format json --report-path <raw>/gitleaks-dir.json` | Catches untracked files (`.env`, local configs). |

Per-change mode: limit Semgrep to the changed files (`git diff --name-only <base>`), and keep osv-scanner and gitleaks on the whole repo (they are fast).

## Phase 2 — Triage

For each candidate, apply the four checks of `owasp-security` "Before Reporting a Finding" (attacker-controlled input, reachable sink, blast radius, every step possible). Drop or downgrade what fails. Dependencies: a CVE in a package that the code never imports, or in a dev-only tool, is Low, not High; say why.

A leaked secret is always a finding, even in history. The fix is **rotation** first, then removal. Removing it from the code does not revoke it.

## Phase 3 — Fix (one target at a time, highest severity first)

1. **Understand.** Read the code path from the entry point to the sink.
2. **Plan.** Name the fix and every instance (search for the same pattern: the `variant-analysis` idea — one bug often has siblings).
3. **Apply** to all instances. Code: the smallest change that closes the path. Dependency: the lowest version that fixes the CVE; check its changelog for breaking changes. If no fixed version exists, stop and list options (pin, replace, mitigate, accept the risk in the profile).
4. **Re-scan** with the same scanner: the finding must be gone and no new one may appear.
5. **Test.** Run the project test command. A red test means the fix is not done.
6. **Ask** before `git commit` or a PR. Show the diff and the re-scan result.

## Output

For `audit-report`: one row per finding with scanner, rule id, file:line, severity after triage, status (`fixed`, `open`, `accepted`, `false positive` + why), and the tool versions.

## Red flags

| Thought | Reality |
|---|---|
| "gitleaks says no leaks found" | Check the commit count first. In a worktree or as root in a container it reads 0 commits and still says "no leaks found". |
| "0 findings, the repo is safe" | It means these rules found nothing. Say which rules ran and what they cannot see (business logic, authorization). |
| "I'll print the secret to check it" | Never. `--redact` and check by rule id and location. |
| "Bump every dependency to latest" | Bump what fixes a reachable CVE. Mass upgrades hide breaking changes. |
| "The test suite is slow, skip it" | An unverified fix is not a fix. |
