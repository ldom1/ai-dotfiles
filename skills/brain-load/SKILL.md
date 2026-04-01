---
name: brain-load
description: Load the current Local Brain project note into context; detect new projects, ask for a CAP to instantiate from the vault project template, and prime Claude with project context.
---

# brain-load

## Purpose

Each codebase session maps to a **project slug** and a note in the Local Brain vault. This skill loads that note into context. If the project is **not** in the vault yet, you **must ask which CAP** (area of responsibility) to attach, then **instantiate** the note from the vault’s **`projects/_template.md`**.

Vault layout this skill expects (PARA + caps):

- **Project notes:** `projects/<slug>.md` (preferred — matches Obsidian `projects/` + `_template.md`)
- **Legacy:** `Projects/<slug>/brief.md` (folder per project + `brief.md` from the skill template only)
- **CAPs:** `caps/<name>.md` — long-term hats (e.g. `developer`, `entrepreneur`)

## Questions — Cursor, Claude Code, and Claude (same skill)

Asking for the CAP or for CAP fields does **not** require a shell script with `read` / `prompt`. The **assistant asks in the current conversation**; the **user answers in the next message** (Cursor agent chat, Claude Code, claude.ai, API, etc.). This SKILL is the single contract: follow it in whatever UI hosts the agent.

- **One turn or several:** you may ask one field per message or send a short numbered form — whichever fits the thread.
- **No silent defaults** for CAP choice or slug still applies everywhere.

## Configuration

`BRAIN_PATH` via **`BRAIN_ENV_FILE`**, **`brain.env`** next to `load.sh`, or **ai-dotfiles `config/brain.env`** (see env resolution in script comments).

**Standalone:** copy this whole folder (`_brain_env.sh`, `load.sh`, `instantiate.sh`, `templates/`, optional `brain.env`). **`instantiate.sh` requires Python 3** (template substitution). The vault must contain **`projects/_template.md`**. If the user picks a **new** CAP, create **`caps/<name>.md`** first using **`templates/cap.md`** (see interview above).

## Slug resolution (priority order)

Use this chain **before** treating the repo as “new”:

1. **`.brain-project`** at git root — first non-empty line
2. **Git remote `origin`** — repo name (`.git` stripped; SSH `git@host:org/repo.git` → `repo`)
3. **Directory name** of cwd
4. **Ask the user once** — then write `.brain-project`

## Scripts (this skill directory)

| Script | Role |
|--------|------|
| `load.sh` | Resolve slug + `BRAIN_PATH`, print note body, or exit `2` with `PROJECT_NOTE_MISSING` |
| `load.sh --slug-only` | Print `slug`, `note`, `mode`, `template_vault`, `caps_dir` (no exit 2) |
| `load.sh --list-caps` | Print `cap:<id>` for each `caps/*.md` |
| `instantiate.sh` | **`--cap <id>`** — copy `_template.md` → `projects/<slug>.md`, set `caps: [[caps/<id>]]`, update `.brain-project` |
| `templates/cap.md` | Scaffold for a **new** `caps/<id>.md` when the user creates a missing CAP (interactive setup) |

## Autonomous execution (session start)

Run **after** `brain-sync start`:

```bash
bash ~/ai-dotfiles/skills/brain-load/load.sh
```

**If exit 0:** read stdout into context **silently** — do not announce unless the user asks.

**If exit 2** — parse stderr for `PROJECT_NOTE_MISSING`:

- **`mode=para_missing`** (vault has `projects/_template.md` or a `projects/` dir):
  1. Run `load.sh --list-caps` and **`ask the user which CAP`** this repo should use (one choice: `developer`, `entrepreneur`, … from the list).
  2. **If the chosen CAP does not exist** (`caps/<id>.md` missing): do **not** fail silently. **In the conversation, run a short interview** (see *Questions — Cursor, Claude…* above) to create **`$BRAIN_PATH/caps/<id>.md`** from **`templates/cap.md`** in this skill (same folder as `load.sh`). Minimum fields to collect:
     - **File id** (slug) — ASCII, no spaces, matches `caps/<id>.md` (e.g. `researcher`). Confirm it matches what they want for `instantiate.sh --cap`.
     - **Display title** — H1 / frontmatter `title` (e.g. `Researcher`).
     - **Mission** — one line after `>` (long-term responsibility).
     - **Objectives** — bullet list (`- …`), can be a single bullet for MVP.
     - **Key resources** — optional bullets (wiki links or paths); default `- _(to complete)_` if empty.
     Replace `{{DATE}}` with today (`YYYY-MM-DD`), then write the file under the vault.
  3. After the CAP file exists, run:
     ```bash
     bash ~/ai-dotfiles/skills/brain-load/instantiate.sh --cap "<their-cap-id>"
     ```
     (from the **project git root** so slug/path resolve correctly; optional: `--slug` / `--path` overrides.)
  4. Re-run `load.sh` and load the new project note into context.

- **`mode=legacy_missing`** (no vault `projects/` layout): offer to create **`Projects/<slug>/brief.md`** from **`templates/brief.md`** in this skill (replace `{{PROJECT_SLUG}}`, `{{DATE}}`). No CAP in frontmatter for this path unless the user asks to align with vault conventions.

**Do not** pick a CAP silently — **always ask** when `para_missing`.

## Edge cases

| Situation | Behavior |
|-----------|----------|
| Note exists (`para` or `legacy`) | Load silently |
| `para_missing` | Ask CAP → `instantiate.sh` → reload |
| `legacy_missing` | Offer skill `templates/brief.md` scaffold |
| `caps/<cap>.md` missing | **Conversation interview** (not a TTY script), write `caps/<id>.md` from **`templates/cap.md`**, then **`instantiate.sh`** |
| Ambiguous slug | Ask once, write `.brain-project` |
| Script / missing `BRAIN_PATH` | Warn once, skip |

## Manual trigger

`/brain-load` — same as running `load.sh` from the project repo.

## CLAUDE.md

```
@../skills/brain-load/SKILL.md
```

Global: `@~/ai-dotfiles/skills/brain-load/SKILL.md`
