---
name: git-commit
description: Validate and write a git commit message following the project's conventional commit convention. Always invoke before running any git commit command.
user-invocable: true
---

# Git Commit Convention

**Always invoke this skill before writing a commit message.**

## Format

```
type(scope): imperative description
```

- One line. Body only when the WHY is non-obvious and can't be inferred from the diff.
- Imperative mood: *add*, *fix*, *update* — not *added*, *fixes*.
- Lowercase after the colon unless a proper noun.

## Types

| Type | When |
|------|------|
| `feat` | New behavior, new capability, new skill |
| `fix` | Bug fix or correction |
| `enh` | Improvement that is neither a fix nor a new feature |
| `doc` | Documentation only |
| `ci` | CI, automation, hooks |

## Scope

**Free-form.** Use the most descriptive word for what was changed — folder name, domain, concern. No fixed vocabulary.

Common examples: `chore`, `design`, `ci`, `vulnerability`, `auth`, `api`, `tests`, `deps`, `config`

`chore` is preferred over `core` for cross-cutting maintenance.

## Validation Checklist

Before committing, confirm:

- [ ] Type is one of: `feat`, `fix`, `enh`, `doc`, `ci`
- [ ] Scope is present and descriptive (always use a scope when the change has a clear domain)
- [ ] Description starts with an imperative verb
- [ ] No trailing period

## Examples

```
feat(chore): apply ruff formatting across codebase
fix(vulnerability): sanitize user input before SQL query
enh(design): extend tier1 NocoDB schema with intelligence columns
feat(ci): add pre-commit hook for commit message validation
fix(deps): pin httpx to ≥0.27 for async client compat
doc(api): document OpenRouter embedding endpoint usage
```
