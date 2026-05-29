---
name: digest
description: >-
  Generates a weekly digest summarising the brain-audit run (what was compiled,
  connected, insights found), writes it to meta/digest-YYYY-MM-DD.md, and
  resets the maintenance clock in meta/last-maintenance.md. Use when: "weekly
  digest", "generate digest", "reset audit clock", or as the final step of a
  full brain-audit.
user-invocable: true
---

# brain-audit:digest

Write the weekly digest and reset the maintenance clock.

> **Wikilink rule:** All internal vault references in the digest file MUST use Obsidian wikilinks: `[[path/to/file]]` (vault-relative, no `.md`, no leading slash). This ensures the digest appears in the backlinks panel of every file it references.

## Step 1 — Load config

```bash
source ~/ai-dotfiles/skills/brain-audit/scripts/_brain_env.sh
mkdir -p "$BRAIN_PATH/meta"
```

## Step 2 — Collect stats

Gather counts from the current session (passed in from the orchestrator, or approximate from recent files):
- `COMPILE_COUNT` — entries promoted in compile step (or 0)
- `CONNECT_COUNT` — wikilinks added in connect step (or 0)
- `INSIGHTS_COUNT` — queries run in insights step (or 0)

## Step 3 — Run digest.sh

```bash
bash ~/ai-dotfiles/skills/brain-audit/scripts/digest.sh \
  "${COMPILE_COUNT:-0}" "${CONNECT_COUNT:-0}" "${INSIGHTS_COUNT:-0}"
```

This writes:
- `$BRAIN_PATH/resources/queries/archive/weekly-digest-YYYY-WNN.md`
- `$BRAIN_PATH/meta/last-maintenance.md` (resets clock)

## Step 4 — Write meta/digest-YYYY-MM-DD.md (Claude-authored summary)

Write to `$BRAIN_PATH/meta/digest-$(date +%Y-%m-%d).md`:

```markdown
---
date: YYYY-MM-DD
type: digest
---

# Brain Audit Digest — YYYY-MM-DD

## What ran
- compile: N entries promoted
- connect: N wikilinks added
- insights: N queries synthesized
- qmd-sync: N files updated in index

## Key takeaways
<2-3 sentences summarising the most important findings from this audit>

## Follow-ups
- [ ] <any action items not yet done>
```

## Step 5 — Remind to sync vault

```
Digest written. Run brain-sync end (or /capture) to commit and push the vault.
Next maintenance: ~7 days from today.
```
