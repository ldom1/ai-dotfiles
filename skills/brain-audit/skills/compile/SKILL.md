---
name: compile
description: >-
  Reads inbox/daily/ notes from the last 30 days, extracts cross-project
  pitfalls and lessons, and writes them as rules to
  resources/operational/ai-agents/pitfalls.md, or to the Rules of a
  resources/knowledge/patterns/*-patterns.md note. Asks inline when an entry is
  ambiguous. Also audits existing rules for project-specific content that
  leaked in. Use when: "compile notes", "promote pitfalls", "review inbox",
  or after /capture.
user-invocable: true
---

# brain-audit:compile

Promote cross-project rules from `inbox/daily/` into `resources/operational/ai-agents/pitfalls.md`. That file is injected into every session, so it holds distilled rules, not incidents. Stack-specific rules go to `resources/knowledge/patterns/*-patterns.md`. Write every rule as in `~/ai-dotfiles/skills/brain-audit/reference/pitfall-rules.md` (bullet shape, ids, budget check). Vault references are `[[slug]]` wikilinks (filename, no folder, no `.md`), never paths.

## 1 — Find recent notes

```bash
source ~/ai-dotfiles/skills/brain-audit/scripts/_brain_env.sh
LOOKBACK=${BRAIN_AUDIT_LOOKBACK_DAYS:-30}
CUTOFF=$(date -d "-${LOOKBACK} days" +%Y-%m-%d 2>/dev/null || date -v-${LOOKBACK}d +%Y-%m-%d)
find "$BRAIN_PATH/inbox/daily/implementation" "$BRAIN_PATH/inbox/daily/plans" "$BRAIN_PATH/inbox/daily/specs" \
     -name "*.md" -newermt "$CUTOFF" 2>/dev/null | sort
```

Stop and tell the user if `BRAIN_PATH` is missing.

## 2 — Classify and promote

For each notable mistake, decision or working approach:

- **Cross-project and cross-stack** (would recur in a different project on a different stack) → search `pitfalls.md`; sharpen the rule that already covers it, otherwise add one bullet under the matching `## <Topic>`, as in `reference/pitfall-rules.md`.
- **Stack-specific** (one tool or platform: Docker/Coolify, Python/Postgres/pandas, Ansible/network, Prometheus) → add it to the `## Rules` list of the matching `resources/knowledge/patterns/*-patterns.md`, not to `pitfalls.md` (step 3).
- **Project-specific** → skip; it belongs in that project's `.claude/memory/CONTEXT.md` Gotchas or DECISIONS.
- **Ambiguous** → ask before moving on:

  ```
  Ambiguous entry in <relative/path.md>:
    "<entry, max 2 sentences>"
  → cross-project rule, or <project>-specific (skip)?
  ```

## 3 — Write pattern notes

A stack-specific rule from step 2 goes to the matching `resources/knowledge/patterns/<topic>-patterns.md`. Append the rule to its `## Rules` list. Never duplicate a rule. Create a new note only when **2+ projects** hit the pattern (Docker, Python, deployment, observability, CI, auth, AI-agent tooling…). Say how many notes you read if you sampled. A new note takes a free letter for its ids: add it to the list in `reference/pitfall-rules.md`. One format:

```markdown
---
title: <Topic> Patterns
created: YYYY-MM-DD
tags: [knowledge, patterns, <topic>]
---

# <Topic> Patterns

## Rules
- <imperative rule + the mechanism in a clause>. ^<letter><n>

## Observed in
- [[<session-log-slug>]] — <one-line context>
```

`Observed in` lists `[[slug]]` links, never paths.

For each contributing project with a `projects/<slug>.md` note, add (if absent) `- [[<topic>-patterns]] — <pattern that applies>` under its existing `## Links` section. The one-pager shape is fixed, so add no new section.

## 4 — Audit existing rules

Re-read `pitfalls.md` (not `archive/` — those logs are frozen). Flag rules that name a specific client/repo, duplicate another rule, or are no longer true; propose remove / merge / keep for each. Finish with the budget check from `reference/pitfall-rules.md`: it must print `— ok`.

## 5 — Report

```
brain-audit:compile complete
  Rules added: N · sharpened: N · pattern notes created / updated: N
  Skipped (project-specific): N · ambiguous resolved: N
  Flagged existing rules: N
```
