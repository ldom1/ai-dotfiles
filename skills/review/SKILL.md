---
name: review
description: Review the current diff against project-specific and generic checklists. Auto-discovers CONTRIBUTING.md and .claude/review/checklist.md.
user-invocable: true
---

# review

Code review grounded in this project's standards. Loads project-specific rules automatically — no wiring required.

## Auto-discovery (always, silently)

Before reviewing, check for these files in order and read each one that exists:

1. `CONTRIBUTING.md` at the project root — project-specific rules (required reviewer checks, naming conventions, domain invariants)
2. `.claude/review/checklist.md` — generic review steps for this project

If neither exists, proceed with the generic checklist below.

## Review steps

1. **Read the diff** — `git diff HEAD` or the staged diff. If a specific file or range was given, scope to that.
2. **Apply CONTRIBUTING.md rules** (if loaded) — flag any violation as a blocking finding.
3. **Apply checklist** (if loaded, else use generic below) — work through each item, report pass/fail per item.
4. **Generic checks** (always run, even when a checklist is loaded):
   - Correctness: logic errors, off-by-one, missed edge cases
   - Abstraction drift: code more complex than the surrounding codebase
   - Cognitive debt: cyclomatic complexity or file length increased without justification
   - Undocumented non-obvious decisions
5. **Output** — structured findings grouped by severity: blocking / warning / suggestion. For each finding: file, line range, rule violated, suggested fix.

## Output format

```
## Review — <date>

### Blocking
- [ ] <file>:<lines> — <rule> — <suggestion>

### Warnings
- [ ] <file>:<lines> — <observation>

### Suggestions
- [ ] <file>:<lines> — <improvement>

### Checklist
- [x] <item from checklist> — passed
- [ ] <item from checklist> — FAILED: <detail>
```

## Rules

- Never approve a diff that has blocking findings.
- Flag cognitive debt in the PR description even if not blocking.
- If CONTRIBUTING.md is missing, suggest creating it from the template at `pratique-ia/templates/CONTRIBUTING-project.md`.
