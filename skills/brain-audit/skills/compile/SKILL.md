---
name: compile
description: >-
  Reads inbox/daily/ notes from the last 30 days, extracts cross-project
  pitfalls and lessons, and writes them as rules to
  resources/operational/ai-agents/pitfalls.md. Asks inline when an entry is
  ambiguous. Also audits existing rules for project-specific content that
  leaked in. Use when: "compile notes", "promote pitfalls", "review inbox",
  or after /capture.
user-invocable: true
---

# brain-audit:compile

Promote cross-project rules from `inbox/daily/` into `resources/operational/ai-agents/pitfalls.md`. That file is injected into every session (it shares the SessionStart hook's ~9.5 KB output budget with the project note and is truncated past it), so it holds distilled rules, not incidents. Vault references are `[[slug]]` wikilinks.

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

- **Cross-project** (would recur in a different project) → search `pitfalls.md`; sharpen the rule that already covers it, otherwise add one bullet under the matching `## <Topic>`: imperative rule + the mechanism in a clause, exact command when that is the fix. No dates, project names or narrative — the session log keeps the story. Merge rules to stay under 6 KB.
- **Project-specific** → skip; it belongs in that project's `.claude/memory/CONTEXT.md` Gotchas or DECISIONS.
- **Ambiguous** → ask before moving on:

  ```
  Ambiguous entry in <relative/path.md>:
    "<entry, max 2 sentences>"
  → cross-project rule, or <project>-specific (skip)?
  ```

## 3 — Audit existing rules

Re-read `pitfalls.md` (not `archive/` — those logs are frozen). Flag rules that name a specific client/repo, duplicate another rule, or are no longer true; propose remove / merge / keep for each.

## 4 — Report

```
brain-audit:compile complete
  Rules added: N · sharpened: N
  Skipped (project-specific): N · ambiguous resolved: N
  Flagged existing rules: N
```
