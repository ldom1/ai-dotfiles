# OWASP coverage of securitypowers

What the vendored `owasp-security` skill (agamm/claude-code-owasp, pin in `.owasp_version`) covers, measured from its files on 2026-11-20. Re-measure after each re-sync. Never infer coverage from a skill's name.

## Covered by `owasp-security`

| Standard | Depth | Where |
|---|---|---|
| OWASP Top 10:2025 (A01–A10) | All 10 categories, attack vectors, unsafe/safe code | `SKILL.md`, `reference/owasp-report.md`, `reference/review-checklist.md` |
| OWASP Top 10 for LLM Applications 2026 | All 10 risks with mitigations | `SKILL.md`, `reference/owasp-report.md` |
| OWASP Top 10 for Agentic Applications 2026 | ASI01–ASI10 | `SKILL.md`, `reference/owasp-report.md` |
| ASVS 5.0.0 | Chapter list, levels, **44 example requirements out of 345** | `reference/owasp-report.md` § ASVS |
| Per-language pitfalls | 20 sections (JS/TS, Python, Java, C#, PHP, Go, Ruby, Rust, Swift, Kotlin, C/C++, Scala, R, Perl, Shell, Lua, Elixir, Dart, PowerShell, SQL) | `reference/languages.md` |
| Config and supply chain (A02, A03) | Containers, Kubernetes, Terraform, web server config, security headers, lockfiles, typosquatting, install scripts, CI/CD, signing and SBOM | `reference/config-and-supply-chain.md` |

## Not covered by `owasp-security`, and where securitypowers fills the gap

| Gap | Filled by |
|---|---|
| Rest of ASVS 5.0 (301 requirements) | `references/asvs-5.0.md`: full grid from the official export. Traceability only. |
| OWASP API Security Top 10 2023 | `references/api-top10-2023.md` |
| Ansible and host configuration | `iac-scan` (KICS, ansible-lint, Trivy), `host-hardening` (ANSSI / CIS via OpenSCAP) |
| Fail-open defaults (fallback secrets, default credentials, debug features) | `references/insecure-defaults/` (Trail of Bits corpus) |
| OWASP WSTG (dynamic testing guide) | Not covered. The Strix skills run dynamic tests; they do not follow WSTG step by step. |
| OWASP Cheat Sheet Series | Not vendored. `audit-report` links the relevant cheat sheet for each finding: https://cheatsheetseries.owasp.org/ |
| OWASP MASVS (mobile) | Not covered (no mobile project). |

## How to state coverage in a report

- Name the standards and the sections the review walked through.
- For ASVS, give counts: `verified`, `failed`, `not applicable`, `not evaluated`. Most will be `not evaluated`; say so.
- Never write "OWASP compliant" or "ASVS L2 compliant".
