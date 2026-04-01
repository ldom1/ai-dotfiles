# Mistral Vibe

## Skills and the `skill` tool

Vibe discovers skills on disk (including this `.vibe/skills/` tree), builds the **`available_skills`** list, and exposes the built-in **`skill`** tool.

Behavior (aligned with Vibe’s implementation):

- Search roots include `~/.vibe/skills/`, project `.vibe/skills/` directories, and **`skill_paths`** entries in the **active** `config.toml`.
- The **system prompt** summarizes available skills (names + short descriptions).
- When a task matches a listed skill, the agent calls **`skill`** with that skill’s **name**; the full `SKILL.md` body (instructions, workflows, bundled resources) is **injected into the conversation context**.

In this repo, `brain-sync` and `brain-load` are wired via symlinks to `../../skills/<id>/` so sources are not duplicated.

To actually **run** the sync/load scripts at the start of work, Vibe still needs the agent to execute bash — see root **`AGENTS.md`** in this repo (injected when the project folder is trusted).

## Trusted folder

The clone must be **trusted** in Vibe, and you should run Vibe with this directory as the working tree (typically `cd` into the clone, then `vibe`), so project discovery picks up `.vibe/skills/`.

## Do not wipe your global config

If you add **`.vibe/config.toml` at the project root**, Vibe may load it **instead of** `~/.vibe/config.toml` while the folder is trusted — which drops your global models/providers. To add skills only, prefer this `.vibe/skills/` layout (or absolute paths in **`skill_paths`** inside **`~/.vibe/config.toml`**).
