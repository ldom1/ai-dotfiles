# Skills

Skills are self-contained directories in [`skills/`](https://github.com/ldom1/ai-dotfiles/tree/main/skills). Claude Code (and Vibe) load `SKILL.md` as slash-command instructions; many skills shell out to `scripts/*.sh` under `~/ai-dotfiles/skills/…`.

Install via `/plugin install <name>@ldom1/ai-dotfiles` where the skill is on the marketplace, or run `bash ~/ai-dotfiles/scripts/install.sh` to symlink all skills from this repo.

## Skill catalogue

| Skill | Slash command | Wiki |
| --- | --- | --- |
| brain-sync | `/brain-sync` | [Skills/Brain-Sync](Skills/Brain-Sync) |
| brain-load | `/brain-load` | [Skills/Brain-Load](Skills/Brain-Load) |
| brain-route | _(invoked by scripts)_ | [Skills/Brain-Route](Skills/Brain-Route) |
| brain-audit | `/brain-audit` | [Skills/Brain-Audit](Skills/Brain-Audit) |
| notion-brain-sync | `/notion-brain-sync` | [Skills/Notion-Brain-Sync](Skills/Notion-Brain-Sync) |
| create-pr | `/create-pr` | [Skills/Create-PR](Skills/Create-PR) |
| server-audit | `/server-audit` | [Skills/Server-Audit](Skills/Server-Audit) |
| graphify | `/graphify` | [Skills/Graphify](Skills/Graphify) |
| token-watch | `/token-watch` | [Skills/Token-Watch](Skills/Token-Watch) |
| token-guard | `/token-guard` | [Skills/Token-Guard](Skills/Token-Guard) |
| finops-audit | `/finops-audit` | [Skills/FinOps-Audit](Skills/FinOps-Audit) |

## Layout (CI-enforced)

Each marketplace skill includes `SKILL.md`, `.claude-plugin/plugin.json`, and a nested `skills/<name>/SKILL.md` symlink for Claude Code discovery. See [Repository Structure](Repository-Structure) in the wiki.
