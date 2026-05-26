---
name: capture
description: End-of-session workflow — write implementation notes, check pitfalls/lessons, sync brain vault. Invoke when user types /capture or asks to end the session.
user-invocable: true
---

# capture

Run this skill when the user types `/capture` or asks to close/end the session.
Execute every step below in order. Do not skip any step, even for short sessions.

## Step 1 — Write implementation notes (ALWAYS)

Resolve `BRAIN_PATH`:
```bash
grep BRAIN_PATH ~/ai-dotfiles/config/brain.env | cut -d= -f2
```

Get today's date: `date +%Y-%m-%d`

Determine the project name from the working directory or `.claude/CLAUDE.md`.

**Target path:** `$BRAIN_PATH/inbox/daily/implementation/<project-name>/<TODAY>-<topic>.md`

- If a file for today already exists in the same project, append to it.
- If nothing substantive happened (lookups only, no writes), still write a one-liner: `Lookup/Q&A session only. No files modified.`

**Format for substantive sessions:**
```markdown
## <topic>

**Goal:** <one line>
**Changes:** <bullet list>
**Commands/tests:** <commands run>
**Follow-ups:** <open questions or next steps, or "none">
```

## Step 2 — Update pitfalls (only if a new mistake pattern was discovered)

File: `$BRAIN_PATH/resources/operational/ai-agents/pitfalls.md`

Append only if this session revealed a **cross-project, generalizable** wrong approach, misunderstanding, or time-wasting pattern — something that could recur in any future project. Project-specific mistakes (wrong config value, wrong partition name, domain misunderstanding for this codebase) do not belong here. Skip if nothing genuinely general applies.

```markdown
## <TODAY> — <project>

**Context:** <what led to the mistake>
**What was wrong:** <the mistake>
**What to do instead:** <the correct approach>
```

## Step 3 — Update lessons learned (only if a non-obvious decision was made)

File: `$BRAIN_PATH/resources/operational/ai-agents/lessons-learned.md`

Append only if a **cross-project, generalizable** lesson was learned — something that would change how Claude approaches similar problems in any future project. Project-specific decisions (architecture choices, domain rules, naming conventions for this codebase) belong in `DECISIONS.md` in the project brain, not here. Skip if nothing genuinely general applies.

```markdown
## <TODAY> — <project>

**Decision:** <what was decided> | **Rejected:** <what was rejected> | **Rationale:** <why>
**Blocker:** <blocker, or NONE>
**Do not repeat:** <specific action to avoid>
---
```

## Step 4 — Sync the vault

```bash
bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh end
```

## Step 5 — Tell the user

Output: `Session documented. You can now close with Ctrl+C.`
