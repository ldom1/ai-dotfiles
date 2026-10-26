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
**Harness changes:** <optional; one row per harness change>
- <component> · <change> · expected: <effect> · check: <metric or command>
**Metrics:** <optional; the `harness-metrics.py` line>
```

Add `**Metrics:**` when `$CLAUDE_SESSION_ID` is set. Run this command and paste its line:

```bash
python3 -I ~/ai-dotfiles/scripts/harness-metrics.py session --id "$CLAUDE_SESSION_ID" --compact
```

A second `/capture` of the same session replaces the line with the same id prefix. If `$CLAUDE_SESSION_ID` is unset (Cursor, Vibe), skip the label and say so. Lookup-only logs get no label.

If the session edited the harness, add one `**Harness changes:**` row per change. The harness is skills, hooks, `AGENTS.md`, the settings template, `pitfalls.md` and pattern notes. `check:` names a number that the SessionEnd metrics line records, or a command. Such numbers are a guard's refusals, a rule's hits and a skill's calls. Leave the verdict empty: `/brain-audit` fills it.

Check the log, then fix every `FAIL` line and run the check again until it prints `OK`:

```bash
python3 ~/ai-dotfiles/skills/capture/scripts/check_log.py "$BRAIN_PATH/inbox/daily/implementation/<slug>/<TODAY>-<topic>.md" --vault "$BRAIN_PATH"
```

This is the history. Details live here, not in the memory files below.

If `$BRAIN_PATH/inbox/daily/checkpoints/<slug>/<TODAY>.md` exists (written by the PreCompact hook before each compaction), use it to recover what happened before the context was compacted. Fold the useful lines into the log, then delete the checkpoint file.

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

`$BRAIN_PATH/resources/operational/ai-agents/pitfalls.md` is injected into every session, so it holds rules, not incidents. A script enforces its 6,000 B cap: `bash ~/ai-dotfiles/scripts/check-pitfalls-budget.sh`. It covers both kinds: a **pitfall** (mistake to avoid) and a **lesson** (approach that worked, worth repeating). Add one only if it would apply in a *different* project on any stack. A rule tied to one tool or platform goes to the `## Rules` list of the matching `resources/knowledge/patterns/*-patterns.md`; a rule tied to this project is a Gotcha or Decision (step 3).

- Search the file first. Before writing, pick one verdict and state it to the user:
  - **Absorb into <existing rule>** — a rule already covers it: sharpen that rule. This is the default.
  - **Improve** — the existing rule is wrong or too vague: rewrite it.
  - **Save** — nothing covers it: add one bullet.
  - **Drop** — one-off, or project-specific (step 3).

  Prefer Absorb: every new bullet competes for the same injected bytes.

  A **lesson** needs an observed contrast. The same task failed or cost more without the approach, and passed with it, in this session. A success seen once is confounded. A session with several changes at once is also confounded. Keep it in the session log with verdict **Drop**.
- Add one bullet under the matching `## <Topic>`: imperative rule + the mechanism in a clause, exact command when that is the fix. No dates, no project names, no narrative — the session log keeps the story.
- End the bullet with its id: the section letter and the next free number, e.g. `^g15`. Letters in `pitfalls.md`: `v` Verification, `d` Diagnosis, `u` Working with the user, `s` Safety and secrets, `o` Vault. Letters in pattern notes: `g` git-patterns, `c` claude-code-patterns, `h` shell-patterns. A rule keeps its id when it moves between files. Never renumber or reuse an id. A merge keeps the lower id and adds the other to `## Retired ids` as `^g7→^g2`.
- For each Absorb or Improve verdict, add `**Pitfall hit:** [[pitfalls#^g6]]` to today's session log (step 2), with the id of the rule hit. For a rule that moved to a pattern note, link that note: `[[git-patterns#^g6]]`. `/brain-audit` counts these lines to find rules worth a sensor.
- After every edit, run `bash ~/ai-dotfiles/scripts/check-pitfalls-budget.sh`. On exit 1, merge rules (Absorb) or move a stack section to a pattern note, then run it again. Do not leave step 4 while it fails.

  ```markdown
  - Check `git worktree list | grep "[<branch>]"` before checking out a branch — two worktrees on one branch move it under each other's files. ^g15
  - Compute forecast tables and gate thresholds with a script from the stated assumptions — hand-typed tables contradict their own rates. ^v12
  ```

## 5. Sync and hand off

```bash
bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh end
```

Then tell the user: `Session documented. You can now close with Ctrl+C.`
