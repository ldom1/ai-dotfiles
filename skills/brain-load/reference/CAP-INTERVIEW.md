# brain-load — CAP Interview Template

When `brain-load` detects `mode=para_missing` and the user's chosen CAP has no `caps/<id>.md` file in the vault, run this conversational interview in the chat (not a shell prompt — the user answers in subsequent messages).

## When to use this

1. `load.sh` exits 2 with `mode=para_missing`
2. `load.sh --list-caps` shows the chosen CAP is **not** in the list
3. The user confirms they want to create a new CAP

## Fields to collect

Ask these in any order — one per message or as a numbered form:

| Field | Stored as | Notes |
|-------|-----------|-------|
| **File id** (slug) | `caps/<id>.md` filename + `instantiate.sh --cap <id>` | ASCII, no spaces, kebab-case. Example: `researcher`, `open-source-dev`. Confirm it matches what they want to type. |
| **Display title** | Frontmatter `title:` and H1 | Human-readable. Example: `Researcher`, `Open Source Developer`. |
| **Mission** | One line after `>` | Long-term responsibility in one sentence. |
| **Objectives** | Bullet list `- …` | 2–5 bullets, or a single MVP bullet. |
| **Key resources** | Optional bullets | Wiki links or paths; default `- _(to complete)_` if empty. |

Replace `{{DATE}}` in the template with today's date (`YYYY-MM-DD`).

## Example interview (one-form style)

> I didn't find a `researcher` CAP in your vault. Let me create it.
>
> Please fill in these fields (or I'll use defaults):
>
> 1. **File id** (slug): `researcher` — confirm or change
> 2. **Display title**: e.g. `Researcher`
> 3. **Mission** (one line): What's the long-term responsibility of this area?
> 4. **Objectives** (2–5 bullets): What are your goals in this area?
> 5. **Key resources** (optional): Any links or paths to reference?

## After collecting fields

1. Write `$BRAIN_PATH/caps/<id>.md` using `reference/templates/cap.md` with substitutions.
2. Run `instantiate.sh --cap "<id>"` from the project git root.
3. Re-run `load.sh` to confirm the note loaded.
4. Announce: _"Project note created and loaded."_

## What NOT to do

- Do not guess a CAP silently.
- Do not use `bash read` prompts — the interview is in the conversation.
- Do not proceed without confirming the file id slug.
- Do not create a CAP with spaces in the filename.
