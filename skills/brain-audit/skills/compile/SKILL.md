---
name: compile
description: >-
  Reads inbox/daily/ notes from the last 30 days, extracts cross-project
  pitfalls and lessons, and writes them to resources/operational/ai-agents/.
  Asks inline when an entry is ambiguous. Also audits existing entries for
  project-specific content that leaked in. Use when: "compile notes",
  "promote pitfalls", "review inbox", or after /capture.
user-invocable: true
---

# brain-audit:compile

Promote cross-project knowledge from `inbox/daily/` to `resources/operational/ai-agents/`.

> **Wikilink rule:** ALL internal vault references written into any file MUST use Obsidian wikilinks: `[[path/to/file]]` (vault-relative, no `.md`, no leading slash). Never use markdown links or plain paths — only wikilinks appear in Obsidian's backlinks panel and graph view.

## Step 1 — Load config

```bash
source ~/ai-dotfiles/skills/brain-audit/scripts/_brain_env.sh
echo "BRAIN_PATH=$BRAIN_PATH"
```

If BRAIN_PATH is empty or the directory does not exist, stop and tell the user.

## Step 2 — Discover recent inbox files

```bash
LOOKBACK=${BRAIN_AUDIT_LOOKBACK_DAYS:-30}
CUTOFF=$(date -d "-${LOOKBACK} days" +%Y-%m-%d 2>/dev/null || date -v-${LOOKBACK}d +%Y-%m-%d)
find "$BRAIN_PATH/inbox/daily/implementation" \
     "$BRAIN_PATH/inbox/daily/plans" \
     "$BRAIN_PATH/inbox/daily/specs" \
     -name "*.md" -newermt "$CUTOFF" 2>/dev/null \
  | sort
```

Read each file. For every notable decision, mistake, or pattern you find, classify it:

| Classification | Criteria | Action |
|---|---|---|
| **cross-project pitfall** | A mistake that could happen in any project | Append to `resources/operational/ai-agents/pitfalls.md` |
| **cross-project lesson** | A generalizable decision or insight | Append to `resources/operational/ai-agents/lessons-learned.md` |
| **project-specific** | Only applies to one project/client | Skip — leave in inbox |
| **ambiguous** | Could be either | Ask user inline (see format below) |

## Step 3 — Promote entries

For each cross-project entry, append to the relevant file using this format:

**pitfalls.md entry:**
```markdown
## YYYY-MM-DD — <short title>

**Context:** <what was happening>
**What was wrong:** <the mistake>
**What to do instead:** <the correct approach>
```

**lessons-learned.md entry:**
```markdown
## YYYY-MM-DD — <project name>

**Decision:** <what was decided> | **Rejected:** <what was not done> | **Rationale:** <why>
**Blocker:** <blocker or NONE>
**Do not repeat:** <specific instruction>
```

## Step 4 — Inline question format for ambiguous entries

When an entry is ambiguous, pause and ask:

```
❗ Ambiguous entry in <relative/path/to/file.md>:
  "<quoted entry text, max 2 sentences>"
→ Is this cross-project or <project>-specific?
  Reply: [cross-project pitfall] / [cross-project lesson] / [project-specific, skip]
```

Wait for the user's answer before continuing to the next entry.

## Step 5 — Audit existing entries

After promoting new entries, read all files in `$BRAIN_PATH/resources/operational/ai-agents/`. Flag:

- **Project-specific content** — mentions a specific client, repo, or tool not universally applicable
- **Duplicates** — two entries describing the same mistake or decision
- **Stale entries** — dated more than 6 months ago with no current relevance

For each flag, show the entry and propose: remove / merge / keep.

## Step 6 — Summary

```
brain-audit:compile complete
  Promoted: N pitfalls, N lessons
  Skipped (project-specific): N
  Ambiguous resolved: N
  Flagged in existing entries: N (see above)
```

Remind user to run `brain-audit:qmd-sync` so new entries are indexed.
