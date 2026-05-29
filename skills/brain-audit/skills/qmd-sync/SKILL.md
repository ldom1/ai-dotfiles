---
name: qmd-sync
description: >-
  Runs qmd update --collection brain to sync the QMD index with the current
  vault state (adds new files, updates changed files, removes deleted files).
  Reports what changed. Use when: "sync qmd", "update qmd index", "reindex
  vault", or after adding/deleting vault files.
user-invocable: true
---

# brain-audit:qmd-sync

Sync the QMD vector index with the current vault state.

## Step 1 — Load config

```bash
source ~/ai-dotfiles/skills/brain-audit/scripts/_brain_env.sh
command -v qmd || { echo "qmd not installed — run: npm install -g @tobilu/qmd"; exit 1; }
[[ -n "${QMD_INDEX_PATH:-}" ]] || { echo "QMD_INDEX_PATH not set in brain.env"; exit 1; }
```

## Step 2 — Run qmd update

```bash
INDEX_PATH="$QMD_INDEX_PATH" qmd update --collection brain 2>&1
```

Read the full output. Extract:
- Files added (new vault notes indexed)
- Files updated (existing notes re-indexed after edits)
- Files removed (deleted notes pruned from index)

## Step 3 — Check index freshness

```bash
ls -la "$QMD_INDEX_PATH"
```

Report the index file's last-modified timestamp. Flag if it is older than 7 days.

## Step 4 — Run embed if needed

If the update output shows >0 files changed, or if the index is older than 7 days, run:

```bash
INDEX_PATH="$QMD_INDEX_PATH" qmd embed --collection brain 2>&1
```

**Important:** On CPU (no GPU), embed shows only a spinner with no progress counter — this is normal. It takes ~1–2 minutes for ~40 pending vectors. Tell the user to expect silence and not interrupt. Confirm completion with `qmd status` after.

## Step 5 — Summary

```
brain-audit:qmd-sync complete
  Files added:   N
  Files updated: N
  Files removed: N
  Index freshness: YYYY-MM-DD HH:MM
  Embeddings refreshed: yes/no
```

If removed > 10, flag: "Large prune — verify vault is intact before relying on semantic search."
