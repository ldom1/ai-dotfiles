# ai-dotfiles

[![CI](https://github.com/ldom1/ai-dotfiles/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ldom1/ai-dotfiles/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/ldom1/ai-dotfiles?sort=semver)](https://github.com/ldom1/ai-dotfiles/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Wiki](https://img.shields.io/badge/docs-wiki-blue)](https://github.com/ldom1/ai-dotfiles/wiki)

[![The ai-dotfiles session loop in 30 seconds](docs/media/ai-dotfiles-workflow.gif)](docs/media/ai-dotfiles-workflow.mp4)

**The outer harness for AI coding agents.** Model + harness = agent. Claude Code, Cursor and Mistral Vibe are the inner harness. ai-dotfiles is the part you own: rules, hooks, skills, memory and cockpit setup, versioned in one repo and linked into each tool on each machine.

## The loop

Each session starts with what the last one learned, and ends by writing it back.

```
  Obsidian vault (Local Brain: project notes, pitfalls, session logs)
        │                                              ▲
        │ SessionStart: brain-sync pull,               │ SessionEnd: brain-sync push
        │ brain-load (project note + pitfalls)         │ (vault commit + push)
        ▼                                              │
  Orca: one workspace per   ──► work with agents ──► /capture
  project; agents by state,      (Claude Code,        session log, project snapshot,
  questions, session history      Cursor, Vibe)       new pitfall rules
        │
        └── weekly /brain-audit: compile notes, link them, turn a pitfall hit twice into a sensor draft
```

- **Remember.** The vault is the memory. A hook loads a bounded slice at session start: the project note and the pitfall rules. `/capture` writes the session back. `/brain-search` finds past decisions.
- **Steer, then check.** Guides (rules, skills) steer the agent before it acts. Sensors (Stop check, hardline tripwire, commit-scope check, local CI before push) check it after. A rule that holds most of the time becomes a sensor.
- **See every agent: Orca.** [Orca](https://github.com/stablyai/orca) is the cockpit: one window lists the agents of every project, their state and their questions. `install.sh` installs and configures it (see [Orca × ai-dotfiles](#orca--ai-dotfiles)).
- **Reuse, never rebuild.** Established upstream skills are vendored and pinned, and a hook warns when a pin falls behind. Ten skills also install alone, as Claude Code plugins.

## What is inside

| Part | What it gives you | Docs |
|------|-------------------|------|
| `AGENTS.md` | One rule file for Claude Code, Cursor and Vibe. `install.sh` generates the per-tool copies. | [brain.md](docs/brain.md#shared-agent-rules-agentsmd) |
| Hooks | Session load and save, pitfalls injection, Stop check, destructive-command tripwire, commit scopes. | [brain.md](docs/brain.md#claude-code-hooks) |
| Local Brain | An Obsidian vault (a git repo) as memory, with QMD semantic search. | [brain.md](docs/brain.md) |
| Review | One Obsidian base (`TASKS_REVIEW`) lists every manual step and open decision of all agents on all projects. | [brain.md](docs/brain.md#review-the-agents-work) |
| Orca | The agent cockpit, installed from its `.deb` on Ubuntu, with versioned settings and the Orca skills. | [Orca × ai-dotfiles](#orca--ai-dotfiles) |
| Skills | `capture`, `brain-*`, `git-promotion`, `grill-me`, `ponytail`, `graphify` and more. `install.sh` links them into each tool. | [skills.md](docs/skills.md) |
| Local CI | Your GitHub workflows with `act`, in a clean clone, before push. | [local-ci.md](docs/local-ci.md) |

## Orca × ai-dotfiles

[Orca](https://github.com/stablyai/orca) runs the agents; ai-dotfiles gives them their rules, skills and memory. Each concern has one owner:

| Concern | Owner | How |
|---|---|---|
| Orca app and its updates | Orca | Native Ubuntu: `install.sh` downloads the `.deb` of the latest release, checks its sha256 and prints `sudo apt install …`. Never when Orca is already installed. Then Orca updates itself. WSL: install Orca on Windows. |
| Orca CLI (`orca-ide`) | Orca | The `.deb` links `/usr/bin/orca-ide`; under WSL the Windows app installs it. `install.sh` checks `orca-ide skills get orca-cli`. |
| Settings (theme, default agent, permissions, notifications, voice…) | ai-dotfiles | `config/orca/settings.json`. `scripts/orca-settings.py seed` before the first launch, `apply` afterwards (Orca closed), `export` to save changes made in Orca. Native Linux only. |
| Keybindings | Orca | Orca's own export and import. |
| Agent hooks in `~/.claude/settings.json` and `.cursor/hooks.json` | Orca | Orca writes them and reinstalls them; `install.sh` keeps them. Never commit these files. |
| Rules, skills, memory | ai-dotfiles | `AGENTS.md`, `skills/` (with the vendored `orca-cli`, `orca-computer-use`, `orchestration`), vault hooks. |
| Agent `PATH` | ai-dotfiles | Orca starts agents through a login zsh that reads only `~/.zshenv`: `install.sh` sources `config/shell-init.sh` (`~/.local/bin`) from it. |
| Session history | Orca reads `~/.claude/projects` | WSL: Windows cannot follow the `~/.claude` symlink, so run `scripts/wsl-claude-mount.sh` once (bind mount). Native Linux: the symlink works. |
| Wait metric (`aif-check.log`) | ai-dotfiles | `aif-agent-hook` logs each question an agent asks in an Orca terminal. |

On a new Ubuntu machine: run `install.sh`, run the `sudo apt install` line it prints, then open Orca. The settings are already there: Orca imports them on its first launch.

## Quick start

```bash
git clone https://github.com/ldom1/ai-dotfiles.git ~/ai-dotfiles
cp ~/ai-dotfiles/config/brain.env.example ~/ai-dotfiles/config/brain.env
# edit brain.env: BRAIN_PATH (your vault, a git repo) and QMD_INDEX_PATH
bash ~/ai-dotfiles/scripts/install.sh
echo 'source ~/ai-dotfiles/config/brain.env' >> ~/.zshrc
```

Run `install.sh` again after each `git pull`. Then index the vault and tag your projects: see [docs/install.md](docs/install.md).

Only want a skill? Add the marketplace in Claude Code, then install a plugin from it ([list](docs/skills.md#install-a-skill)):

```
/plugin marketplace add ldom1/ai-dotfiles
/plugin install grill-me@ldom1-ai-dotfiles
```

## Design principle

**The AI tools never know about ai-dotfiles.** Files inside `.claude/`, `.cursor/`, `.vibe/` are written as if they are the native config directories (`~/.claude`, `~/.cursor`, etc.). They contain no references to the repo structure, no "ai-dotfiles" framing, no awareness of the versioning layer. Skills invoke scripts via `~/ai-dotfiles/skills/…` because that's the real filesystem path — but config files never explain *why* things are at that path.

## Docs

- [Install](docs/install.md): setup, what `install.sh` does, dependencies, repo structure.
- [Local Brain, hooks and rules](docs/brain.md)
- [Skills](docs/skills.md)
- [Local CI](docs/local-ci.md)
- [Changelog](CHANGELOG.md), [Wiki](https://github.com/ldom1/ai-dotfiles/wiki), [Contributing](CONTRIBUTING.md)

## License

[MIT](LICENSE) © Louis Giron
