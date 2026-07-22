---
name: review
description: Code review that auto-discovers project-specific rules from CONTRIBUTING.md and .claude/skills/review/SKILL.md.
user-invocable: true
---

# review

Structured code review grounded in this project's standards. Loads project-specific rules automatically — no configuration required.

## Auto-discovery (always, silently)

Before reviewing, read each of these files if it exists:

1. `CONTRIBUTING.md` at the project root — project-specific rules, domain invariants, naming conventions
2. `.claude/skills/review/SKILL.md` — project-level checklist override

If neither exists, fall back to the generic checklist below.

## Review steps

1. **Read the diff** — `git diff HEAD` for unstaged, `git diff --staged` for staged, `git diff main...HEAD` for the full branch. Scope to the file or range specified by the user if given.
2. **Apply CONTRIBUTING.md rules** (if loaded) — flag every violation as a blocking finding.
3. **Apply checklist** (from `.claude/skills/review/SKILL.md` if loaded, else generic below).
4. **Generic checks** (always run regardless of loaded files):
   - Correctness: logic errors, off-by-one, edge cases, missing null guards
   - Abstraction: code more complex than the surrounding codebase warrants
   - Cognitive load: cyclomatic complexity or file length increased without justification
   - Security: command injection, SQL injection, hardcoded secrets, insecure defaults
   - Non-obvious decisions left without explanation

## Output format

Group findings by severity. For each finding: file, line range, rule violated, suggested fix.

| Severity | Meaning |
|---|---|
| **Blocking** | Must be fixed before merge |
| **Warning** | Should be addressed; can be deferred with justification |
| **Suggestion** | Nice to have; optional |

End with a one-line verdict: ✅ Ready to merge / ⚠️ Needs attention / ❌ Blocking issues found.
