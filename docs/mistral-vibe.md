# Mistral Vibe and this repository

[Mistral Vibe](https://docs.mistral.ai/mistral-vibe/introduction/quickstart) can load the same Agent Skills layout as Claude Code: one folder per skill with a `SKILL.md` file.

## How skills are discovered

Vibe merges search directories (see [Agents & Skills](https://docs.mistral.ai/mistral-vibe/agents-skills)):

- **Global:** `~/.vibe/skills/`
- **Project:** any `.vibe/skills/` directory found under the working tree (bounded walk)
- **Optional:** `skill_paths` in whichever `config.toml` is **actually loaded** for that session

Each immediate subdirectory that contains a `SKILL.md` becomes one skill, named after the folder (the frontmatter `name` should match that folder name).

## `available_skills` and the `skill` tool

After discovery, skills show up for the agent as **`available_skills`** (summarized in the system prompt).

The built-in **`skill`** tool takes a `name` argument: it loads that skill from the skill manager, reads `SKILL.md`, and **injects the content** into the thread so specialized instructions and workflows apply when the task fits that skill.

## Layout in `ai-dotfiles`

This repo exposes `brain-sync` and `brain-load` through **`.vibe/skills/`** as symlinks to `skills/brain-sync` and `skills/brain-load` (no duplicated files).

Typical requirements:

1. Working directory = repository root (or equivalent).
2. Folder marked **trusted** in Vibe (see [Configuration](https://docs.mistral.ai/mistral-vibe/introduction/configuration), trusted folders).

## Pitfall: project `config.toml`

If you create **`.vibe/config.toml`** at the project root, Vibe may use it **in place of** `~/.vibe/config.toml` when the project is trusted, which removes global providers/models. To extend skills only, use `.vibe/skills/` (as here) or add absolute paths under **`skill_paths`** in **`~/.vibe/config.toml`**.
