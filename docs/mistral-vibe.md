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

**Slash commands:** with `user-invocable: true` in the skill frontmatter (the default in Vibe’s schema), you can type **`/brain-sync`** or **`/brain-load`** in the chat input. That loads the skill content into the conversation the same way — it does **not** execute `sync.sh` or `load.sh`; you still need a bash step (or ask the agent to run it).

## Layout in this repository

Every skill under **`skills/<name>/`** with a `SKILL.md` is symlinked from **`.vibe/skills/<name>`** (and from **`.claude/skills/<name>`** for Claude Code). See [skills.md](skills.md).

Typical requirements:

1. Working directory = repository root (or equivalent).
2. Folder marked **trusted** in Vibe (see [Configuration](https://docs.mistral.ai/mistral-vibe/introduction/configuration), trusted folders).

## Brain-sync / brain-load at session start (not automatic)

Vibe has **no** Cursor-style hook that runs shell when a session opens. The **`skill`** tool only **loads text** into the thread when the model calls it; it does not execute `sync.sh` or `load.sh` by itself.

To make startup explicit for this repo, edit **`.vibe/AGENTS.md`** (canonical). Vibe merges **`AGENTS.md`** files from the **current working directory upward** to the [trusted-folder](https://docs.mistral.ai/mistral-vibe/introduction/configuration) root — it does **not** look for `AGENTS.md` only inside `.vibe/`. This repo therefore keeps a **symlink** `AGENTS.md` at the repository root pointing to `.vibe/AGENTS.md` so the loader sees the same content when your cwd is the clone root.

If nothing runs on a new session, check:

- **CWD** — start Vibe from the repo you care about (`cd …/ai-dotfiles` then `vibe`, or equivalent).
- **Trust** — the folder must be trusted; otherwise project instructions from `AGENTS.md` may not load.
- **Symlink** — on Windows, enable `git config core.symlinks true` before checkout if root `AGENTS.md` must point at `.vibe/AGENTS.md`; otherwise duplicate or copy the file at the root.
- **Model behavior** — the model must still **invoke bash**; instructions are not executed by the runtime automatically.

You can also paste “run brain-sync start and brain-load” as your first message.

## Pitfall: project `config.toml`

If you create **`.vibe/config.toml`** at the project root, Vibe may use it **in place of** `~/.vibe/config.toml` when the project is trusted, which removes global providers/models. To extend skills only, use `.vibe/skills/` (as here) or add absolute paths under **`skill_paths`** in **`~/.vibe/config.toml`**.
