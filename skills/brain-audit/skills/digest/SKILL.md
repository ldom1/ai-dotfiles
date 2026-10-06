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

Close an audit run: stats file, maintenance clock, and a short human summary. Vault references are `[[slug]]` wikilinks, so the digest shows up in each referenced note's backlinks.

## 1 — Run digest.sh

Use the counts from this run (0 for a step that didn't run): rules added/sharpened by `compile`, knowledge files touched by `connect`, questions answered by `insights`.

```bash
bash ~/ai-dotfiles/skills/brain-audit/scripts/digest.sh "$COMPILE_COUNT" "$CONNECT_COUNT" "$INSIGHTS_COUNT"
```

It writes `resources/queries/archive/weekly-digest-YYYY-WNN.md` and resets `meta/last-maintenance.md`.

## 2 — Write `meta/digest-YYYY-MM-DD.md`

```markdown
---
date: YYYY-MM-DD
type: digest
---

# Brain Audit Digest — YYYY-MM-DD

## What ran
- compile: N rules added/sharpened in [[pitfalls]]
- connect: N knowledge files ([[<topic>-patterns]], …)
- insights: N questions → [[YYYY-MM-DD]] (inbox/insights)
- queries: [[YYYY-MM-DD-knowledge-gaps]], [[YYYY-MM-DD-roadmap]]
- promote: N candidates → sensor drafts to review: [[YYYY-MM-DD-<slug>]], … (list every file in `inbox/sensors/`; "none" if empty)

## Key takeaways
<2–3 sentences: the findings that need the user's attention>

## Follow-ups
- [ ] <action items not done during the run>
```

Then tell the user: digest written, next maintenance in ~7 days, and the vault is committed by `brain-sync end` / `/capture`.
