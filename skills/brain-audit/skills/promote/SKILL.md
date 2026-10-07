---
name: promote
description: >-
  Counts how often each pitfall rule was hit in recent session logs and drafts
  a sensor (hook, stop check, lint rule or test) for each rule hit in two or
  more sessions. Writes drafts to inbox/sensors/ and never installs anything.
  Use when: "draft sensors", "turn recurring pitfalls into hooks", "which rules keep recurring", or
  after compile in a full brain-audit.
user-invocable: true
---

# brain-audit:promote

A rule that holds most of the time wants to be a sensor. This step finds the rules that recur and drafts their sensors. The user reviews each draft. Nothing installs itself. Vault references are `[[slug]]` wikilinks.

## 1 — Count

`/capture` step 4 writes one `**Pitfall hit:** [[pitfalls#^v3]]` line per Absorb or Improve verdict. Run the counter:

```bash
source ~/ai-dotfiles/skills/brain-audit/scripts/_brain_env.sh
python3 ~/ai-dotfiles/skills/brain-audit/scripts/count-pitfall-hits.py "$BRAIN_PATH" --days "${BRAIN_AUDIT_LOOKBACK_DAYS:-30}"
```

The script maps retired ids to their current id (`## Retired ids` in `pitfalls.md`). It counts distinct session logs per id. It marks an id `candidate` at 2 sessions or more. It marks `skip` an id that has a draft in `inbox/sensors/` or a `(sensor: …)` suffix on its rule. If it prints `0 candidates`, report the counts and stop.

## 2 — Draft

For each `candidate`, read its rule (the line ending with `^<id>` in `pitfalls.md` or a `*-patterns.md` note) and its citing logs. Write `inbox/sensors/YYYY-MM-DD-<slug>.md` with:

```markdown
---
date: YYYY-MM-DD
type: sensor-draft
pitfall: ^v3
---

# Sensor draft: <slug>

**Rule:** <the rule text>
**Cited in:** [[log-1]], [[log-2]]
**Kind:** PreToolUse hook | Stop check | lint rule | pytest | not mechanizable (<reason>)
**Installs at:** <file or setting where it would live>

## Draft (≤ 40 lines)
<code>

## Examples
- match: <input the sensor must catch>
- not_match: <input the sensor must let through>
```

Pick the kind whose guarantee you can state exactly. If no sensor can check the rule, write `not mechanizable` with the reason and no code. The `pitfall:` field is how the counter finds the draft later, so keep it.

## 3 — Report

```
brain-audit:promote complete
  Window: N days · ids with hits: N
  Candidates: N · drafts written: N · skipped (draft or sensor exists): N
  Drafts: [[YYYY-MM-DD-<slug>]], …
```

The user accepts a draft by asking for it as a normal task. After it ships, add `(sensor: <hook name>)` before the rule's id in `pitfalls.md`. A rule with a sensor is a merge candidate when the budget is tight.
