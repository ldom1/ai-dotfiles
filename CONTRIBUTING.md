# Contributing

Thanks for your interest in contributing to ai-dotfiles. Contributions are welcome — whether it's a new skill, a bug fix, or documentation.

## What you can contribute

- **New skills** — self-contained AI skills compatible with Claude Code and Mistral Vibe
- **Improvements to existing skills** — better SKILL.md docs, more robust scripts
- **Bug fixes** — broken scripts, incorrect paths, edge case handling
- **Documentation** — GitHub wiki pages in `.wiki/`, reference files inside skills

## Skill requirements

Every skill must follow the canonical layout:

```
skills/<name>/
├── SKILL.md                   # required — frontmatter: name, description, user-invocable
├── scripts/                   # all .sh scripts (POSIX-compatible)
│   └── *.sh
├── reference/                 # supporting docs, templates, examples
│   └── *.md
└── .claude-plugin/
    └── plugin.json            # required — name, version, description, author
```

The CI checks that every skill has `SKILL.md` and `.claude-plugin/plugin.json`.

Shell scripts must pass `shellcheck --severity=warning`.

## Wiki publishing

Edit pages directly in `.wiki/` (this is the GitHub wiki repository clone), then publish intentionally:

```bash
bash scripts/update-wiki.sh
```

## SKILL.md frontmatter

```yaml
---
name: your-skill-name        # matches the folder name
description: One sentence.   # shown in Claude's available_skills list
user-invocable: true         # false if the skill is auto-loaded only
---
```

## Commit format

```
type(scope): imperative description
```

Types: `feat`, `fix`, `enh`, `doc`, `ci`. Scope: `skill`, `claude`, `cursor`, `config`, `scripts`, `core`.

See `skills/create-pr/reference/GIT-COMMITS.md` for the full reference.

## Pull request process

1. Fork the repository.
2. Create a branch: `feature/<name>`, `fix/<name>`, or `enh/<name>`.
3. Run `shellcheck` on any new or modified `.sh` files.
4. Validate any `.json` files with `python3 -m json.tool <file>`.
5. Open a PR against `main`. Include what the skill does and how you tested it.

## Releasing (maintainers only)

Push a semver tag to trigger an automatic GitHub Release:

```bash
git tag v1.2.3
git push origin v1.2.3
```

The `release.yml` workflow creates the release and generates a changelog from commits since the previous tag.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
