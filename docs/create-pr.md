# create-pr

Skill for opening GitHub PRs following ai-dotfiles conventions. Canonical skill: [`skills/create-pr/SKILL.md`](../skills/create-pr/SKILL.md).

## Branch naming

| Change type | Prefix | Example |
|-------------|--------|---------|
| Feature | `feature/` | `feature/oauth-login` |
| Bugfix | `fix/` | `fix/null-ref-cache` |
| Improvement | `enh/` | `enh/faster-sync` |

Use kebab-case. If already on a suitably named branch, keep it.

## Commit format

```
type(scope): imperative description
```

Quick types: `feat`, `fix`, `enh`, `doc`, `ci`. Full reference: [`docs/git-commits.md`](git-commits.md).

## Workflow

1. `git status` — check working tree
2. Run tests if the project has them
3. `git fetch origin` + rebase onto primary branch
4. Commit uncommitted changes (conventional message)
5. `git push -u origin HEAD`
6. `gh pr create` — `--fill` when commits carry good titles, else `--title` + `--body`

## Usage

Invoke with `/create-pr` in Claude Code or Mistral Vibe.

Available on the marketplace:

```
/plugin install create-pr@ldom1/ai-dotfiles
```
