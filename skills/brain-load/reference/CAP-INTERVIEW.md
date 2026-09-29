# brain-load — New CAP interview

Use when `load.sh` exits 2 with `mode=para_missing` and the CAP the user picked is not in `load.sh --list-caps`. Collect the fields in chat — one form or one question per message:

| Field | Stored as | Notes |
|-------|-----------|-------|
| **File id** | `caps/<id>.md`, `instantiate.sh --cap <id>` | kebab-case, no spaces (it becomes a filename and a CLI arg); confirm it with the user |
| **Display title** | frontmatter `title:` + H1 | e.g. `Open Source Developer` |
| **Mission** | the `>` line | one sentence |
| **Objectives** | `- …` bullets | 2–5 |
| **Key resources** | bullets, `[[slug]]` links | optional; default `- _(to complete)_` |

Then write `$BRAIN_PATH/caps/<id>.md` from `templates/cap.md` (`{{DATE}}` = today), run `instantiate.sh --cap <id>` from the project git root, and re-run `load.sh` to confirm.
