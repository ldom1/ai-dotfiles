---
name: create-pr
description: Open a GitHub PR using gh and ai-dotfiles git conventions
disable-model-invocation: true
---

# Create PR

Use only when the user runs **`/create-pr`** or explicitly asks for this workflow.

## Branch naming

| Change type | Branch prefix | Example |
|-------------|---------------|---------|
| Feature | `feature/` | `feature/oauth-login` |
| Bugfix | `fix/` | `fix/null-ref-cache` |
| Improvement (not feat/fix) | `enh/` | `enh/faster-sync` |

Use kebab-case after the prefix. If already on a suitably named branch, keep it.

## Commit messages

Format: **`type(scope): imperative description`** (one line unless context needs a body).

Types and scopes: `~/ai-dotfiles/docs/git-commits.md` (in-repo). Quick types: `feat`, `fix`, `enh`, `doc`, `ci`.

## Steps

1. `git status` — working tree as expected; stash or commit WIP intentionally.
2. If the project has tests, run the usual command (from project docs or last session).
3. `git fetch origin` — rebase onto the repo’s primary branch when appropriate (e.g. `git rebase origin/main`). If the default branch differs, use that remote ref.
4. Commit with conventional message if changes are uncommitted.
5. `git push -u origin HEAD`
6. **`gh pr create`** — prefer `--fill` when commits carry good titles; else `--title` + `--body` with *what*, *why*, *how tested*.

## Checklist

- [ ] Branch prefix matches intent
- [ ] Commits follow `docs/git-commits.md`
- [ ] PR description is enough for a reviewer without chat history
