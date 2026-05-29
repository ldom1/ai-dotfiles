---
name: brain-audit
description: >-
  Full vault maintenance pipeline: compile inbox notes into cross-project
  knowledge, connect notes via QMD semantic links, generate insights from
  query templates, sync QMD index, and produce a weekly digest.
  Triggers on: "audit my notes", "weekly audit", "vault maintenance",
  "run brain-audit", or when brain-route decides maintenance mode.
user-invocable: true
---

# brain-audit

Full vault maintenance — runs all 5 steps in sequence with human checkpoints.

## Before starting

```bash
source ~/ai-dotfiles/skills/brain-audit/scripts/_brain_env.sh
echo "BRAIN_PATH=$BRAIN_PATH"
```

Confirm BRAIN_PATH is set and the vault is a git repo. If `brain-sync start` has not been run yet, ask the user to run it first.

## Step 1 — Compile

Invoke `brain-audit:compile`.

Wait for the user to resolve any inline ambiguous-entry questions before continuing.

## Step 2 — QMD Sync

Invoke `brain-audit:qmd-sync`.

This ensures the index reflects any new entries written in Step 1 before semantic search runs.

## Step 3 — Connect

Invoke `brain-audit:connect`.

Show the git diff and wait for user approval before committing wikilinks.

## Step 4 — Insights

Invoke `brain-audit:insights`.

## Step 5 — Queries

Invoke `brain-audit:queries`.

## Step 6 — Digest

Invoke `brain-audit:digest`.

Pass the counts from steps 1–4 so the digest reflects what actually ran.

## Final step

```
brain-audit complete.
Run: bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh end
(or /capture) to commit and push all vault changes.
```
