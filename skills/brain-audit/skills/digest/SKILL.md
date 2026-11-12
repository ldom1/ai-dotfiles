---
name: digest
description: >-
  Writes a digest note summarising the brain-audit run (what was compiled,
  connected, insights found) to meta/digest-YYYY-MM-DD.md, and resets the
  maintenance clock in meta/last-maintenance.md. Use when: "weekly
  digest", "generate digest", "reset audit clock", or as the final step of a
  full brain-audit.
user-invocable: true
---

# brain-audit:digest

Close an audit run: maintenance clock and a short human summary. Vault references are `[[slug]]` wikilinks, so the digest shows up in each referenced note's backlinks.

## 1 — Reset the clock

```bash
bash ~/ai-dotfiles/skills/brain-audit/scripts/digest.sh
```

It resets `meta/last-maintenance.md` and writes nothing else. SessionStart reads `Epoch Seconds` from that file to print "maintenance due" after 7 days.

## 2 — Write `meta/digest-YYYY-MM-DD.md`

Use the counts from this run (0 for a step that did not run).

```markdown
---
date: YYYY-MM-DD
type: digest
---

# Brain Audit Digest — YYYY-MM-DD

## What ran
- compile: N rules added/sharpened in [[pitfalls]]
- connect: N notes linked ([[<topic>-patterns]], …)
- insights: N questions → [[YYYY-MM-DD]] (inbox/insights)
- queries: [[YYYY-MM-DD-knowledge-gaps]], [[YYYY-MM-DD-roadmap]]
- promote: N candidates → sensor drafts to review: [[YYYY-MM-DD-<slug>]], … (list every file in `inbox/sensors/`; "none" if empty)

## Key takeaways
<2–3 sentences: the findings that need the user's attention>

## Follow-ups
- [ ] <action items not done during the run>
```

Then tell the user: digest written, next maintenance in ~7 days, and the vault is committed by `brain-sync end` / `/capture`.
