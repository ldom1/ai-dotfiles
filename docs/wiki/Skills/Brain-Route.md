# Skills/Brain-Route

Session router: reads vault health (maintenance age, raw backlog) and chooses **normal** mode (brain-load) vs **maintenance** (brain-audit). Invoked from `brain-sync` after a successful pull; not a user slash command by default.

**Canonical instructions:** [`skills/brain-route/SKILL.md`](https://github.com/ldom1/ai-dotfiles/blob/main/skills/brain-route/SKILL.md)

**Script:** `bash ~/ai-dotfiles/skills/brain-route/scripts/route.sh`
