---
name: brain-load
description: Load the current Local Brain project note into context; detect new projects, ask for a CAP to instantiate from the vault project template, and prime Claude with project context.
user-invocable: true
---

# brain-load

Map the current codebase to a **project note** in the Local Brain vault and load it into context. If the project is new, ask which **CAP** (area of responsibility) it belongs to and create the note from the vault template.

## Quick start

```bash
# Run from your project's git root after brain-sync start:
bash ~/ai-dotfiles/skills/brain-load/scripts/load.sh
```

Exit 0 → project note printed to stdout (load into context silently).
Exit 2 + `PROJECT_NOTE_MISSING` on stderr → new project, follow the CAP flow below.

## Vault layout

```
$BRAIN_PATH/
├── projects/
│   ├── _template.md     ← vault project template (required for PARA mode)
│   └── <slug>.md        ← active project notes
├── caps/
│   └── <id>.md          ← areas of responsibility (developer, entrepreneur, …)
└── Projects/            ← legacy layout (folder-per-project + brief.md)
    └── <slug>/
        └── brief.md
```

See `reference/VAULT-LAYOUT.md` for full structure and PARA conventions.

## Slug resolution

The script determines the project slug in this order:

1. `.brain-project` file at git root — first non-empty line
2. Git remote `origin` — repo name (SSH `git@host:org/repo.git` → `repo`)
3. Directory name of `cwd`
4. Ask the user once — then write `.brain-project`

## Scripts

| Script | Flags | Role |
|--------|-------|------|
| `scripts/load.sh` | _(none)_ | Resolve slug + BRAIN_PATH, print note or exit 2 |
| `scripts/load.sh` | `--slug-only` | Print slug, note path, mode, template_vault, caps_dir |
| `scripts/load.sh` | `--list-caps` | Print `cap:<id>` for each `caps/*.md` |
| `scripts/instantiate.sh` | `--cap <id>` | Copy `_template.md` → `projects/<slug>.md`, update `.brain-project` |

## Autonomous execution (session start)

Run **after** `brain-sync start`:

```bash
bash ~/ai-dotfiles/skills/brain-load/scripts/load.sh
```

**Exit 0** → read stdout into context **silently** (no announcement).

**Exit 2 + `mode=para_missing`** (vault has a `projects/` dir or `_template.md`):

1. Run `--list-caps`, then **ask the user in the conversation which CAP** to use.
2. If the chosen CAP has **no** `caps/<id>.md`: run a **conversational interview** (not a shell prompt) to gather: file id, display title, mission, objectives, key resources. Write `$BRAIN_PATH/caps/<id>.md` from `reference/templates/cap.md`. See `reference/CAP-INTERVIEW.md` for the full interview template.
3. Run `instantiate.sh --cap "<id>"` from the project git root.
4. Re-run `load.sh` and load the new note into context.

**Exit 2 + `mode=legacy_missing`** (no `projects/` layout): offer to create `Projects/<slug>/brief.md` from `reference/templates/brief.md`.

**Critical rules:**
- Never choose a CAP silently — always ask the user.
- Never use a shell `read` prompt — the interview happens in the chat conversation.
- Never fail silently on missing `BRAIN_PATH` — warn once, then skip.

## Configuration

`BRAIN_PATH` via **`BRAIN_ENV_FILE`**, **`brain.env`** beside `scripts/load.sh`, or **`config/brain.env`** at the ai-dotfiles root. See `reference/brain.env.example`.

**Standalone:** copy the full `brain-load/` folder (all scripts + reference/). `scripts/instantiate.sh` requires **Python 3**. The vault must have `projects/_template.md` for PARA mode.

## Edge cases

| Situation | Behavior |
|-----------|----------|
| Note exists (para or legacy) | Load silently |
| `para_missing` | Ask CAP → `instantiate.sh` → reload |
| `legacy_missing` | Offer `reference/templates/brief.md` scaffold |
| `caps/<cap>.md` missing | Conversational interview → write cap file → `instantiate.sh` |
| Ambiguous slug | Ask once, write `.brain-project` |
| Missing `BRAIN_PATH` or script | Warn once, skip |

## Manual trigger (Mistral Vibe)

Type **`/brain-load`** to inject this skill into the chat. Running `scripts/load.sh` still requires a bash step.

**Direct script:**

```bash
bash ~/ai-dotfiles/skills/brain-load/scripts/load.sh         # run from project git root
bash ~/ai-dotfiles/skills/brain-load/scripts/load.sh --list-caps
bash ~/ai-dotfiles/skills/brain-load/scripts/instantiate.sh --cap developer
```

## Files

```
skills/brain-load/
├── SKILL.md
├── scripts/
│   ├── load.sh           ← slug resolve + print note (or exit 2)
│   ├── instantiate.sh    ← create projects/<slug>.md from _template.md
│   └── _brain_env.sh     ← config loader (sourced by load.sh + instantiate.sh)
└── reference/
    ├── brain.env.example
    ├── VAULT-LAYOUT.md   ← expected vault structure and PARA conventions
    ├── CAP-INTERVIEW.md  ← conversation template for creating a new CAP
    └── templates/
        ├── brief.md      ← legacy project note scaffold
        └── cap.md        ← new CAP file scaffold
```
