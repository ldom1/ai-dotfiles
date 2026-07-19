---
name: git-commit
description: Validate and build a git commit message following type(scope): description convention. MUST be invoked before ANY git commit command — no exceptions.
user-invocable: true
---

# Git Commit Convention

**This skill MUST run before every `git commit`. Never run `git commit` without completing this skill first.**

## Format

```
type(scope): imperative description
```

- One line. Body only when WHY is non-obvious.
- Imperative mood: *add*, *fix*, *update* — not *added*, *fixes*.
- Lowercase after the colon unless a proper noun.

## Merge commits — exempt

A merge commit (two parents) records a merge of two histories, not authored work. Git's standard messages — `Merge branch 'X' into Y`, `Merge pull request #N from ...`, `Merge remote-tracking branch ...` — are exempt from the type(scope) convention and the hook allows them unchanged. Do not force a merge commit message into `type(scope):` form.

## Types (fixed)

| Type | When |
|------|------|
| `feat` | New behavior, new capability |
| `fix` | Bug fix or correction |
| `enh` | Improvement — neither fix nor new feature |
| `doc` | Documentation only |
| `ci` | CI, automation, hooks |

## Scopes (finite, per project type)

Scopes are defined in `~/ai-dotfiles/skills/git-commit/scopes.json`.

| Project type | Detection markers | Valid scopes |
|---|---|---|
| `ai-dotfiles` | `skills/brain-sync`, `.claude/skills` | `skill`, `claude`, `config`, `scripts`, `core`, `ci`, `design`, `docs` |
| `python` | `pyproject.toml`, `uv.lock`, `setup.py` | `core`, `ci`, `design`, `docs`, `api`, `tests`, `config`, `vulnerability` |
| `nextjs` | `next.config.*` | `core`, `ci`, `design`, `docs`, `ui`, `api`, `auth`, `tests`, `config`, `vulnerability` |
| `ansible` | `ansible.cfg`, `site.yml`, `roles/` | `core`, `ci`, `design`, `docs`, `roles`, `inventory`, `config`, `tests`, `vulnerability` |

## Process (run before every commit)

### Step 1 — Detect project type

Check repo root for detection markers (in order listed in `scopes.json`). Use `git rev-parse --show-toplevel` to find root.

**If project type is unknown:**
1. Tell the user: "Unknown project type — I need to define the scope list for this repo."
2. Propose a scope list based on the project structure.
3. **Wait for user validation before doing anything.**
4. Once validated: update `scopes.json` (add new entry with detect markers + scopes).
5. Commit the change: `feat(skill): add <type> project type to git-commit scope registry`
6. Continue to Step 2.

### Step 2 — Validate the commit message

Check the proposed message against `^(feat|fix|enh|doc|ci)(\([^)]+\))?: .+`

If format is wrong: correct it and confirm with the user before committing.

### Step 3 — Validate the scope

Check the scope against the locked list for the detected project type.

**If scope is not in the locked list:**
1. Tell the user: "Scope `<x>` is not in the `<project-type>` list."
2. Propose adding it, with a one-line description of what it covers.
3. **Wait for user validation before doing anything.**
4. Once validated: update `scopes.json` (append scope to the project type's list).
5. Commit the change: `feat(skill): add <scope> scope to <project-type> in git-commit registry`
6. Continue to Step 4.

### Step 4 — Commit

All checks pass. Run `git commit -m "<validated message>"`.

## Hard Rules

- **Never run `git commit` before completing Steps 1–3.**
- **Never add a new scope or project type without explicit user validation.**
- **Never modify `scopes.json` without immediately committing the change.**
- The `scopes.json` file is the single source of truth — the table above is a snapshot.
