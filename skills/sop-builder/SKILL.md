---
name: sop-builder
description: Turn a described process, or an existing informal note (or several notes to reconcile), into a Standard Operating Procedure with a fixed 7-section shape — Purpose, Scope, Prerequisites, Steps, Verification, Rollback, Owner/Last updated — validated by a script so every SOP has the same structure. Use whenever the user asks to write, create, document, formalize, or reconcile an SOP, runbook, recovery procedure, or "how do we do X" process note, even if they don't say the word "SOP" explicitly.
user-invocable: true
---

# SOP Builder

An SOP is only useful if someone who didn't write it can follow it later without guessing at the
shape of the document. This skill trades freeform generation for a fixed template: every SOP it
produces has the same seven sections, in the same order, so reproducibility beats flexibility.
It does one thing — turn source material into (or reconcile it into) exactly one SOP document.
It never executes the process it documents, never monitors it, and doesn't manage version history
beyond a `last-updated` field.

## Process

1. **Identify the source material.** This might be a process the user describes conversationally,
   one informal note, or several documents to reconcile (e.g. a raw implementation log plus an
   existing partial SOP for the same thing). If sources disagree on a detail, prefer the most
   recent or most concrete one and say so inline in the output — don't silently merge
   contradictory claims into one, since that erases exactly the kind of nuance an SOP reader needs.

2. **Copy `template.md`** (in this skill's directory) as the starting point for the new document.
   Never rename, reorder, or drop a section — if a section genuinely doesn't apply to this
   process, its body is the literal text `N/A`, not an omitted heading. A missing section reads as
   an oversight; an explicit `N/A` reads as a decision.

3. **Fill each section**, matching the level of detail to what the source material actually
   supports. A one-command rollback is one line; a process with multiple recovery paths (e.g.
   "container lost" vs. "host lost" needing different recovery) gets sub-bullets under `Rollback`.
   Content and depth vary between SOPs — the seven-section shape never does.

4. **Owner and Last updated**: ask the user for the owner's name if it isn't already clear from
   context. Use today's date for `last-updated`.

5. **Validate before declaring done.** Run:
   ```bash
   python3 <path-to-this-skill>/scripts/validate_sop.py <output-file>
   ```
   It checks that all seven sections are present, in the required order, and non-empty (or `N/A`).
   If it fails, fix the reported issue and re-run — but cap this at **two** fix attempts. If it's
   still failing after that, stop and show the user the validator's exact output rather than
   looping — a repeated failure usually means the source material doesn't fit the template
   cleanly, which is worth a human's judgment, not another automated retry.

6. **Choose the output location.** SOPs live at
   `$BRAIN_PATH/resources/knowledge/sops/<slug>-sop.md` (resolve `BRAIN_PATH` via
   `grep BRAIN_PATH ~/ai-dotfiles/config/brain.env`), matching the naming already used there
   (`authelia-hp-elite-server-sop.md`, `coolify-hp-elite-server-sop.md`, ...). Never silently
   overwrite an existing file with reconciled content — if the target name is already taken and
   this run is meant to produce a new, separate document, pick a distinct but clearly related
   filename and tell the user which one and why.

## Non-goals

This skill does not execute, automate, or monitor the procedure it documents, and it does not keep
a changelog or diff history beyond the single `last-updated` field. If the user wants ongoing
version tracking, that's a job for git history on the SOP file itself, not for this skill.
