# Git Commit Conventions

Format: `<type>(<scope>): <imperative description>`

- One line for most commits. Body only when context is non-obvious.
- Imperative mood: *add*, *fix*, *update* (not *added* / *fixes*).
- Lowercase after the colon unless using a proper noun.

## Types

| Type | Use |
|------|-----|
| `feat` | New behavior, new skill, new user-facing capability |
| `fix` | Bug fix or correction |
| `enh` | Improvement that is not a bugfix nor a new feature |
| `doc` | Documentation only |
| `ci` | CI, automation, release hooks only |

## Scopes

Scopes are **free-form** — use the most descriptive word for the domain or concern changed.

Common scopes: `chore` (cross-cutting maintenance), `design`, `ci`, `vulnerability`, `auth`, `api`, `tests`, `deps`, `config`, `skill`, `claude`, `scripts`

`chore` is preferred over `core` for repo-wide or cross-cutting work.

If nothing obvious fits, use the folder name at repo root.

## Examples

```
feat(chore): apply ruff formatting across codebase
feat(skill): add git-commit convention enforcement hook
fix(vulnerability): sanitize user input before SQL query
enh(design): extend NocoDB schema with intelligence columns
fix(skill): handle missing BRAIN_PATH in load script
doc(api): document OpenRouter embedding endpoint usage
ci: add workflow to validate shell scripts
```

## References

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Tim Pope — A Note About Git Commit Messages](https://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html)
