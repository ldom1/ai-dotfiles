---
name: brain-load
description: Load the current Local Brain project note into context on demand (or after Claude Code / Cursor CLI hooks). Cursor IDE Agent must not auto-run at session start — use /brain-load or an explicit ask.
user-invocable: true
---

# brain-load

Print the current project's vault one-pager (`projects/<slug>.md`) plus its repo memory files (`.claude/memory/`), or create the note if the project is new.

**When to run:** Claude Code (`brain-session-start.sh`) and Cursor Agent CLI (`.cursor/hooks/session-start.sh`) already run it at session start and inject stdout, so re-run only when the user asks, `/brain-load` is invoked, or the hook reported `PROJECT_NOTE_MISSING`. Cursor IDE Agent has no hooks by design: run it only on request. Mistral Vibe: `/brain-load` loads this skill; the script still needs a bash step.

```bash
bash ~/ai-dotfiles/skills/brain-load/scripts/load.sh              # from the project git root
bash ~/ai-dotfiles/skills/brain-load/scripts/load.sh --slug-only  # slug=, note=, mode=, template_vault=, caps_dir=
bash ~/ai-dotfiles/skills/brain-load/scripts/load.sh --list-caps  # cap:<id> per caps/*.md
```

**Slug:** first line of `.brain-project` at the git root → `origin` repo name → directory name.

**Output (exit 0):** `--- PROJECT NOTE ---` block, then — if `.claude/memory/settings.json` exists — `--- PROJECT BRAIN ---` with the files in its `read_on_session_start` (default `OBJECTIVES.md`, `CONTEXT.md`). Take it in as context without announcing it. The Claude Code hook sets `BRAIN_LOAD_SKIP_MEMORY=1` (memory comes from the project `CLAUDE.md` imports) and injects only the first 30 lines, so keep the note short.

## New project (exit 2, `PROJECT_NOTE_MISSING`)

**`mode=para_missing`** (vault has `projects/`):

1. Run `--list-caps` and ask the user which CAP the project belongs to — the CAP is their call, not something to infer.
2. If that CAP has no `caps/<id>.md`, collect its fields in chat (see `reference/CAP-INTERVIEW.md`) and write it from `reference/templates/cap.md`. Shell `read` prompts don't work in an agent session.
3. From the project git root: `bash ~/ai-dotfiles/skills/brain-load/scripts/instantiate.sh --cap <id>` — renders `$BRAIN_PATH/_templates/project-template.md` into `projects/<slug>.md` (needs Python 3) and writes `.brain-project`.
4. Re-run `load.sh`.

The note is the project's one-pager (≤ 450 words, rewritten in place): one-sentence summary, idea, objectives, how it works, where, memory pointer, links — shape in `scripts/instantiate.sh`. No journal or dated entries — history belongs in `inbox/daily/implementation/<slug>/`. `/brain-init-project` fills it properly.

**`mode=legacy_missing`** (vault without `projects/`): offer `Projects/<slug>/brief.md` from `reference/templates/brief.md`.

Missing `BRAIN_PATH`: say so once and continue without the note. Config lookup: `$BRAIN_ENV_FILE` → `scripts/brain.env` → `~/ai-dotfiles/config/brain.env` (template: `reference/brain.env.example`). Vault layout: `reference/VAULT-LAYOUT.md`.
