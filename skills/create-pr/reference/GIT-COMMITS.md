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

| Scope | Typical paths |
|-------|---------------|
| `core` | Cross-cutting or repo-wide |
| `skill` | `skills/**` |
| `claude` | `.claude/**` |
| `cursor` | `.cursor/**` |
| `config` | `config/**` |
| `scripts` | `scripts/**` |
| `prompts` | `prompts/**` |
| `ci` | `.github/**` |

If nothing fits, use the folder name at repo root.

## Examples

```
feat(skill): add brain sync skill
fix(skill): handle missing BRAIN_PATH in load script
enh(cursor): tighten brain-sync rule wording
doc: link git commit guide from README
ci: add workflow to validate shell scripts
feat(claude): add RTK hook for token proxy
```

## References

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Tim Pope — A Note About Git Commit Messages](https://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html)
