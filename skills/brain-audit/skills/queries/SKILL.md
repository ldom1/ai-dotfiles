---
name: queries
description: >-
  Two structured vault analyses: (1) knowledge-gaps — surveys resources/knowledge/
  and cross-references recent implementation notes to find underdocumented topics;
  (2) roadmap — aggregates all active project folders + recent implementation logs
  into a consolidated status view. Archives results to resources/queries/archive/.
  Use when: "knowledge gaps", "what am I missing", "project roadmap", "where are
  my projects", "what should I document".
user-invocable: true
---

# brain-audit:queries

Two analyses, each archived to `resources/queries/archive/`. Vault references are `[[slug]]` wikilinks; files whose name repeats in every project folder (`ROADMAP`, `OBJECTIVES`…) need the folder to be unambiguous: `[[<slug>/ROADMAP]]`.

```bash
source ~/ai-dotfiles/skills/brain-audit/scripts/_brain_env.sh
TODAY=$(date +%Y-%m-%d)
CUTOFF=$(date -d '-30 days' +%Y-%m-%d 2>/dev/null || date -v-30d +%Y-%m-%d)
mkdir -p "$BRAIN_PATH/resources/queries/archive"
```

## 1 — Knowledge gaps → `$TODAY-knowledge-gaps.md`

Survey what exists (`find "$BRAIN_PATH/resources/knowledge" -name '*.md'` — title, number of `##` patterns, `created`), then read recent implementation notes (`-newermt "$CUTOFF"`) and look for tools, failure modes or domains that recur across 3+ notes or 2+ projects with no knowledge file. Check the previous `*-knowledge-gaps.md` and say which gaps are still open.

```markdown
---
date: YYYY-MM-DD
type: query-result
query: knowledge-gaps
---

# Knowledge Gaps — YYYY-MM-DD

## Coverage
| Knowledge file | Patterns | Created |
|---|---|---|
| [[docker-patterns]] | N | YYYY-MM-DD |

## Write this week
1. **<topic>** — why: seen in [[<note>]], [[<note>]]; seed: <2 sentences>

## Write this month
1. **<topic>** — why: <rationale>

## Still open from last run
- <gap> (first flagged YYYY-MM-DD)
```

## 2 — Roadmap → `$TODAY-roadmap.md`

In scope: project folders `projects/<slug>/` (mirrors of each repo's `.claude/memory/`). Flat `projects/<slug>.md` notes without a folder are not.

```bash
ls -d "$BRAIN_PATH/projects"/*/
# last session log per project
for d in "$BRAIN_PATH/inbox/daily/implementation"/*/; do
  last=$(ls "$d" | sort | tail -1); [[ -n "$last" ]] && echo "$(basename "$d"): $last"
done
```

Per folder read `ROADMAP.md`, `OBJECTIVES.md`, `CONTEXT.md`; flag folders missing `ROADMAP.md`. For projects active in the last 30 days, pull open items from the latest session log's `**Follow-ups:**`.

```markdown
---
date: YYYY-MM-DD
type: query-result
query: roadmap
---

# Project Roadmap — YYYY-MM-DD

## Active
| Project | Last activity | Current focus | Next step |
|---|---|---|---|
| [[<slug>/ROADMAP]] | YYYY-MM-DD | <from ROADMAP Now> | <one action> |

## Stalled (no session log in 30 days) or missing ROADMAP.md
| Project | Last activity | Note |
|---|---|---|

## Open follow-ups
- [ ] <item> — [[<session-log-slug>]]
```

Report both output paths.
