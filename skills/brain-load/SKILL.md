---
name: brain-load
description: Load the current project brief from the Local Brain Obsidian vault into context at session start. Resolves the project slug automatically, reads the brief, and silently primes Claude with project context.
---

# brain-load

## Purpose

Each project in Local Brain has a `brief.md` that captures its goal, stack, key decisions, current status, and open questions. This skill resolves the current project slug, locates the corresponding brief, and loads it into Claude's context — silently, without interrupting the user.

## Configuration

Brain path is read from `config/brain.env` in the ai-dotfiles repo:

```bash
BRAIN_PATH=/path/to/your/vault
```

Project briefs live at:

```
$BRAIN_PATH/Projects/<slug>/brief.md
```

The helper script is at `skills/brain-load/load.sh`.

## Slug resolution (priority order)

Claude **must** resolve the project slug using this exact priority chain:

1. **`.brain-project` file** at the repo root — read its first non-empty line as the slug (e.g. `artelys-hpc`)
2. **Git remote** — run `git remote get-url origin`, extract the repository name (last path segment, strip `.git`)
3. **Directory name** — use `basename "$PWD"` as the slug
4. **Ask the user once** — if all three above are ambiguous or unavailable, ask: *"Which Local Brain project does this repo map to? (e.g. artelys-hpc)"* — then write the answer to `.brain-project` at the repo root

## Autonomous execution rules

Claude Code **must** execute these steps automatically at session start, after brain-sync completes.

### Session start

Run immediately after `brain-sync start`:

```bash
bash ~/ai-dotfiles/skills/brain-load/load.sh
```

**What it does:**
1. Sources `config/brain.env` to get `BRAIN_PATH`
2. Resolves the project slug using the priority chain above
3. Reads `$BRAIN_PATH/Projects/<slug>/brief.md`
4. Prints the brief content to stdout (captured by Claude as context)

**After running the script, Claude must:**
- Read the brief content into context silently
- Do **not** summarize or acknowledge the brief to the user unless they ask
- Do **not** announce that the brief was loaded
- **Only** speak up in these two cases:
  - Brief file not found → offer to create it from the template (see below)
  - Slug is ambiguous and all auto-detection methods failed → ask the user once

### If the brief doesn't exist

When `$BRAIN_PATH/Projects/<slug>/brief.md` is missing, Claude must offer:

> "No brief found for project **`<slug>`** in Local Brain. Want me to create one at `Projects/<slug>/brief.md`?"

If the user confirms, copy `skills/brain-load/templates/brief.md` to `$BRAIN_PATH/Projects/<slug>/brief.md`, replacing `{{PROJECT_SLUG}}` with the resolved slug and `{{DATE}}` with today's date (`YYYY-MM-DD`), then open the file for the user to fill in.

## Edge case summary

| Situation | Behavior |
|---|---|
| `.brain-project` present | Use it as slug, skip all other detection |
| No git remote | Fall through to directory name |
| Git remote is SSH (`git@github.com:org/repo.git`) | Extract `repo` as slug |
| Brief exists | Load silently, no announcement |
| Brief missing | Offer to create from template |
| Slug ambiguous | Ask user once, write `.brain-project` |
| Script not found | Warn once, continue session |
| `BRAIN_PATH` not set | Warn once, skip brief loading |

## Manual trigger

```
/brain-load          # resolve slug + load brief
```

Or directly:

```bash
bash ~/ai-dotfiles/skills/brain-load/load.sh
```

## CLAUDE.md snippet

Add this line to your project or global `CLAUDE.md` after the brain-sync line, so the brief is loaded each session:

```
@../skills/brain-load/SKILL.md
```

Or if using the global `~/.claude/CLAUDE.md`:

```
@~/ai-dotfiles/skills/brain-load/SKILL.md
```
