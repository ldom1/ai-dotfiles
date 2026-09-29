---
name: capture
description: End-of-session workflow — write the session log, refresh the project memory, add cross-project pitfalls, sync the brain vault. Invoke when user types /capture or asks to end the session.
user-invocable: true
---

# capture

Goal: the next session — any agent, any project — starts with the right context and nothing stale. Write for Claude, not for a human reader: terse, current-state, one fact per line. Vault references are `[[slug]]` wikilinks, never paths.

Only Claude Code has a SessionEnd reminder; under Cursor and Mistral Vibe, `/capture` must be invoked manually.

## 1. Resolve

```bash
grep BRAIN_PATH ~/ai-dotfiles/config/brain.env | cut -d= -f2
bash ~/ai-dotfiles/skills/brain-load/scripts/load.sh --slug-only   # slug=<project>
date +%Y-%m-%d
```

## 2. Session log (always)

`$BRAIN_PATH/inbox/daily/implementation/<slug>/<TODAY>-<topic>.md` — append if today's file covers the same thread. Lookup-only session: one line, `Lookup/Q&A only. No files modified.`

```markdown
## <topic>

**Goal:** <one line>
**Changes:** <bullets: what changed and where; PR/commit ids>
**Commands/tests:** <only commands worth re-running>
**Follow-ups:** <next steps, or "none">
```

This is the history. Details live here, not in the memory files below.

## 3. Project memory (only what changed)

Files: `<repo>/.claude/memory/` (fallback `$BRAIN_PATH/projects/<slug>/`). Base the update on this session's log, not on older notes.

| File | Rule |
|---|---|
| `CONTEXT.md` | Snapshot — **rewrite in place**: `Live now`, `In flight`, `Blockers / open questions`, `Gotchas`, `Recent history` (≤ 5 `[[session-log]]` links). Drop what is no longer true; never prepend dated banners. |
| `DECISIONS.md` | One line per live decision: `- **<decision>** — <why> (<date>)`. Replace a superseded line instead of adding a contradicting one. |
| `ROADMAP.md` | Move finished items out (they belong in CHANGELOG); add new follow-ups under `Now` / `Next` / `Later` / `Open debt`. |
| `ARCHITECTURE.md` | Only durable structure: stack, modules, data flow, invariants. |

Project-specific traps discovered this session go to `CONTEXT.md` → `Gotchas` (one line each). Ask the user before reversing a decision, removing an architecture claim, or changing roadmap direction.

## 4. Pitfalls & lessons (only if cross-project)

`$BRAIN_PATH/resources/operational/ai-agents/pitfalls.md` is injected into every session (keep it ≤ 6 KB: it shares the hook's ~9.5 KB output budget with the project note and is truncated past it), so it holds rules, not incidents. It covers both kinds: a **pitfall** (mistake to avoid) and a **lesson** (approach that worked, worth repeating). Add one only if it would apply in a *different* project; otherwise it is a project Gotcha or Decision (step 3).

- Search the file first; if a rule already covers it, sharpen that rule instead of adding one.
- Add one bullet under the matching `## <Topic>`: imperative rule + the mechanism in a clause, exact command when that is the fix. No dates, no project names, no narrative — the session log keeps the story.

  ```markdown
  - Check `git worktree list | grep "[<branch>]"` before checking out a branch — two worktrees on one branch move it under each other's files.
  - Compute forecast tables and gate thresholds with a script from the stated assumptions — hand-typed tables contradict their own rates.
  ```

## 5. Sync and hand off

```bash
bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh end
```

Then tell the user: `Session documented. You can now close with Ctrl+C.`
