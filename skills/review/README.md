# Review — Code Review Skill

Structured code review that auto-discovers project-specific rules. No configuration in `AGENTS.md` required.

**Full guide:** [Wiki — 06 Claude Skills and Artelys Standards](../../.wiki/06-Claude-Skills-and-Artelys-Standards.md)

## Reference files (auto-discovered)

| File | Purpose | Template |
|------|---------|----------|
| `CONTRIBUTING.md` (project root) | Project-specific review rules | [`templates/project/CONTRIBUTING.md`](../../templates/project/CONTRIBUTING.md) |
| `.claude/skills/review/SKILL.md` | `/review` skill — checklist + output format | [`templates/project/.claude/skills/review/SKILL.md`](../../templates/project/.claude/skills/review/SKILL.md) |

## Quick start

```bash
# Copy the skill and CONTRIBUTING template into your project
cp -r pratique-ia/templates/project/.claude/skills/review .claude/skills/
cp pratique-ia/templates/project/CONTRIBUTING.md CONTRIBUTING.md
# → fill in CONTRIBUTING.md with project-specific rules

# Run a review
/review
```
