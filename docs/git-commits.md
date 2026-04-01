# Git commit messages

Conventions for this repo: short, readable, machine-friendly prefixes.

## Format

```
<type>(<scope>): <imperative description>
```

- **One line** for most commits. Add a blank line and a body only when context is non-obvious.
- **Imperative mood** — *add*, *fix*, *update* (not *added* / *fixes*).
- **Lowercase** after the colon unless you use a proper noun (`feat(claude): …`).

## Types

| Type | Use |
|------|-----|
| `feat` | New behavior, new skill, new user-facing capability |
| `fix` | Bug fix or correction |
| `enh` | Improvement that is not a bugfix nor a new feature (refine UX, perf, ergonomics) |
| `doc` | Documentation only |
| `ci` | CI, automation, release hooks only |

## Scopes

Pick the area that best matches the change. When several files move together, choose the **primary** touch point.

| Scope | Typical paths |
|-------|----------------|
| `core` | Cross-cutting or repo-wide (README, multiple top-level areas) |
| `skill` | `skills/**` |
| `doc` | `docs/**` (use `doc` type if the commit is *only* docs) |
| `claude` | `.claude/**` |
| `cursor` | `.cursor/**` |
| `config` | `config/**` (examples/templates; not secrets) |
| `scripts` | `scripts/**` |
| `prompts` | `prompts/**` |
| `ci` | `.github/**`, workflow files |

If nothing fits, abbreviate to the **folder name** at repo root (e.g. `feat(scripts): …`). Avoid inventing a new scope every time — reuse the table above.

## Examples

```
feat(skill): add brain sync skill
fix(skill): handle missing BRAIN_PATH in load script
enh(cursor): tighten brain-sync rule wording
doc: link git commit guide from README
ci: add workflow to validate shell scripts
feat(claude): add RTK hook for token proxy
fix(core): correct install path in quick start
```

## References

- [Conventional Commits](https://www.conventionalcommits.org/) — same shape (`type(scope): …`); we use `enh` and scopes tailored to this repo.
- [Tim Pope — Git commit messages](https://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html) — length and imperative style.
