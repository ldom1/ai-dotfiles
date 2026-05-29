---
name: queries
description: >-
  Two structured vault analyses: (1) knowledge-gaps — surveys resources/knowledge/
  and cross-references recent implementation notes to find underdocumented topics;
  (2) roadmap — aggregates all active project notes + recent implementation logs
  into a consolidated status view. Archives results to resources/queries/archive/.
  Use when: "knowledge gaps", "what am I missing", "project roadmap", "where are
  my projects", "what should I document".
user-invocable: true
---

# brain-audit:queries

Two structured analyses: knowledge coverage gaps and project roadmap. Both archive results for Obsidian backlinks.

> **Wikilink rule:** ALL internal vault references MUST use Obsidian wikilinks: `[[path/to/file]]` (vault-relative, no `.md`, no leading slash).

## Prerequisites

```bash
source ~/ai-dotfiles/skills/brain-audit/scripts/_brain_env.sh
TODAY=$(date +%Y-%m-%d)
mkdir -p "$BRAIN_PATH/resources/queries/archive"
```

---

## Query 1 — Knowledge Gaps

**Goal:** find what's underdocumented relative to what the vault actually talks about.

### Step 1 — Survey existing knowledge files

```bash
ls "$BRAIN_PATH/resources/knowledge/"
ls "$BRAIN_PATH/resources/operational/ai-agents/"
```

For each `.md` in `resources/knowledge/`: note title, number of `##` sections (patterns), creation date from frontmatter.

### Step 2 — Find topics mentioned but not documented

```bash
# Topics appearing in recent implementation notes without a knowledge file
find "$BRAIN_PATH/inbox/daily/implementation" -name "*.md" -newermt "$(date -d '-30 days' +%Y-%m-%d 2>/dev/null || date -v-30d +%Y-%m-%d)" \
  | xargs grep -h "^\*\*" 2>/dev/null | sort | uniq -c | sort -rn | head -30
```

Read the 5 most recent implementation notes in full. Look for:
- Recurring tools, frameworks, or patterns not covered by any `resources/knowledge/` file
- Topics referenced 3+ times across different projects
- Domains present in projects but absent from knowledge files (e.g., CI/CD, auth, frontend, database)

### Step 3 — Write knowledge-gaps archive

Write to `$BRAIN_PATH/resources/queries/archive/$TODAY-knowledge-gaps.md`:

```markdown
---
date: YYYY-MM-DD
type: query-result
query: knowledge-gaps
---

# Knowledge Gaps — YYYY-MM-DD

## Coverage Overview

| Knowledge file | Patterns | Last updated |
|---|---|---|
| [[resources/knowledge/docker-patterns]] | N | YYYY-MM-DD |
| ... | | |

## Tier 1 — Write this week

1. **`resources/knowledge/<topic>.md`**
   - Why: mentioned in [[project-a]], [[project-b]] — no dedicated file
   - Seed content: <2-sentence description of what it should cover>

## Tier 2 — Write this month

1. **`resources/knowledge/<topic>.md`**
   - Why: <rationale>

## What looks good

- <knowledge files with solid coverage — 1 line each>
```

---

## Query 2 — Roadmap

**Goal:** one consolidated view of all active projects — status, current objectives, open items, next step.

Only projects that have a **folder** in `projects/` are in scope (they have `ROADMAP.md`, `OBJECTIVES.md`, etc.). Flat `.md` files in `projects/` are not project folders — skip them.

### Step 1 — Discover project folders

```bash
ls -d "$BRAIN_PATH/projects"/*/ 2>/dev/null
```

For each folder, read:
- `ROADMAP.md` — current milestones and their status
- `OBJECTIVES.md` — what the project is trying to achieve
- `DECISIONS.md` (if present) — any pending or recent decisions

### Step 2 — Cross-reference recent activity

```bash
# Last implementation note per project (folder name = project slug)
find "$BRAIN_PATH/inbox/daily/implementation" -name "*.md" \
  | sed 's|.*/implementation/\([^/]*\)/.*|\1|' | sort -u \
  | while read proj; do
      last=$(find "$BRAIN_PATH/inbox/daily/implementation/$proj" -name "*.md" 2>/dev/null | sort | tail -1)
      [[ -n "$last" ]] && echo "$proj: $last"
    done
```

For each project with a recent implementation note, read it and extract the `## Follow-ups` section.

### Step 3 — Write roadmap archive

Write to `$BRAIN_PATH/resources/queries/archive/$TODAY-roadmap.md`:

```markdown
---
date: YYYY-MM-DD
type: query-result
query: roadmap
---

# Project Roadmap — YYYY-MM-DD

## Active

| Project | Last activity | Milestone / current focus | Next step |
|---|---|---|---|
| [[projects/artelys-crystal-hpc/ROADMAP]] | YYYY-MM-DD | <milestone from ROADMAP.md> | <one action> |
| ... | | | |

## Stalled / no recent activity

| Project | Last activity | Note |
|---|---|---|
| [[projects/xyz/ROADMAP]] | YYYY-MM-DD | no implementation notes in 30 days |

## Open follow-ups (consolidated)

- [ ] <item> — [[inbox/daily/implementation/project/file]]
- [ ] <item> — [[inbox/daily/implementation/project/file]]
```

---

## Step 4 — Summary

```
brain-audit:queries complete
  knowledge-gaps → resources/queries/archive/YYYY-MM-DD-knowledge-gaps.md
  roadmap        → resources/queries/archive/YYYY-MM-DD-roadmap.md
```
