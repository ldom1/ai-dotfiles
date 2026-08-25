---
name: find-security-vulnerabilities-in-code
description: Find security vulnerabilities in a codebase or repository with Strix — a white-box AI security review that reads your source, reasons about the actual data flow and authorization model, then exploits what it finds in a live sandbox so every reported issue has a working proof-of-concept instead of a noisy static-analysis alert. Covers injection, XSS, SSRF, broken access control and IDOR, insecure deserialization, secrets in code, unsafe dependencies, and business-logic flaws. Use when the user asks to security-scan, security-review, or audit their code, repo, or pull request for vulnerabilities.
license: Apache-2.0
metadata:
  author: usestrix
  homepage: https://docs.strix.ai
---

# Find security vulnerabilities in code

**Authorized use only.** Strix exploits what it finds — it runs real proof-of-concept attacks in a sandbox, not static pattern matching. Only ever point it at a local path or repo the user owns (their own checkout, their own deployed app). If the user names a bare external hostname, domain, or IP instead of a local path or their own repo, stop and confirm ownership or explicit written authorization before running anything — do not treat "just try it" as authorization for a third party's asset.

White-box security review with Strix: the agents read the source to build a model of routes, sinks, and authorization checks, then attempt real exploitation. Findings come with a proof-of-concept, so the output is a short list of proven issues rather than the hundreds of "potential" hits a pattern-matching scanner produces.

## Prerequisites

- **Docker running** — check with `docker info`. The first scan pulls the sandbox image automatically.
- **Strix installed** — check with `strix --version`. Install if missing:
  ```bash
  curl -sSL https://strix.ai/install | bash   # or: pipx install strix-agent
  ```
- **LLM configured** — two environment variables:
  ```bash
  export STRIX_LLM="anthropic/claude-sonnet-5"   # any LiteLLM model id
  export LLM_API_KEY="<provider api key>"
  ```
  Ask the user for these if unset. Never hardcode or commit keys.

Always use `-n` (non-interactive/headless) — the default TUI blocks agents. Always set `--max-budget` unless the user says otherwise.

## Run it

```bash
# Local working tree
strix -n -t ./ --scan-mode standard --max-budget 15

# A GitHub repo the user owns, given directly
strix -n -t https://github.com/org/app --max-budget 15

# Monorepo: point at the service that matters, not the whole tree
strix -n -t ./services/checkout --max-budget 20

# Only what a branch changed (whole-repo review is wasteful on a large repo)
strix -n -t ./ --scope-mode diff --diff-base origin/main --max-budget 10
```

A local path is mounted into the sandbox **writable**, so the agents can modify it. Run against a clean checkout.

Two things sharply improve results:

1. **Add a running instance of the app.** `-t ./ -t http://host.docker.internal:3000` lets the agents confirm exploitability against live behavior instead of reasoning about it statically — this is the difference between "this looks unsafe" and a validated finding. If nothing is running, static-only findings should be described as unconfirmed.
2. **Scope the review.** Point at the risky subtree and say what matters:
   ```bash
   strix -n -t ./services/api --max-budget 15 \
     --instruction "Focus on the authorization layer in src/auth and every route under src/routes/admin. Multi-tenant app: tenant id comes from the JWT. Flag any query that filters by object id without also filtering by tenant."
   ```
   Tenancy model, trust boundaries, and which inputs are attacker-controlled are things the agents cannot infer reliably — tell them.

## Read the results

In `strix_runs/<run>/`: `penetration_test_report.md` (start here), `vulnerabilities/*.md` (one per finding, with PoC and remediation), `vulnerabilities.json` / `.csv`, `findings.sarif` (upload to code scanning), `run.json`.

Before reporting to the user, open each finding and check the PoC actually demonstrates impact. Report file and line alongside the exploit so the fix is obvious.

Exit `0` means nothing exploitable was proven in what was analyzed — not that the codebase is clean. Check `run.json` status and cost against `--max-budget`, and note which paths went unreviewed if the run was capped.

## Complementary tooling

This is exploit-validated review, not an exhaustive inventory. Keep a dependency scanner (SCA) and secret scanning in place for complete coverage of known-CVE dependencies and committed credentials; use this for the logic, authorization, and injection bugs those tools structurally cannot find.

## Fix and verify

Hand results to `fix-security-vulnerabilities-with-strix` (vendored alongside this skill): patch the root cause (the shared authorization helper, not the one route), then re-run Strix to prove the exploit no longer works.

## Not vendored

Strix ships more skills upstream (`penetration-testing-with-strix`, `managed-pentesting-with-strix`, `ci-security-scanning-with-strix`, `owasp-top-10-testing`, `web-app-penetration-testing`, `application-security-testing`, `api-security-testing`) at [usestrix/strix](https://github.com/usestrix/strix/tree/main/skills). Only this white-box code-review skill and its fix/verify companion were vendored here — the general black-box pentest skill accepts a bare URL/domain/IP as target, which is a materially different risk for a personal-projects dotfiles repo. CI PR-gating and the managed app.strix.ai cloud are per-project decisions; read the upstream skill directly if a specific project wants either.
