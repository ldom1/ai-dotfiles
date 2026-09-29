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

Refresh the QMD index mid-session. `brain-sync end` already runs `qmd update` + `qmd embed` at every session end, so this is only needed when notes changed during the current session (e.g. before `connect`/`insights` in a full audit).

```bash
source ~/ai-dotfiles/skills/brain-audit/scripts/_brain_env.sh
command -v qmd || { echo "qmd not installed — run: npm install -g @tobilu/qmd"; exit 1; }
[[ -n "${QMD_INDEX_PATH:-}" ]] || { echo "QMD_INDEX_PATH not set in brain.env"; exit 1; }
INDEX_PATH="$QMD_INDEX_PATH" qmd update --collection brain 2>&1
```

Report files added / updated / removed from the output. If any changed, embed:

```bash
pgrep -af 'qmd.*embed' && echo "embed already running — wait for it"   # two writers corrupt the SQLite index
INDEX_PATH="$QMD_INDEX_PATH" qmd embed --collection brain 2>&1
```

On CPU, `embed` shows only a spinner for 1–2 minutes. A Bash tool timeout does not kill it: check `pgrep` before assuming it died, and never start a second one. Confirm with `INDEX_PATH="$QMD_INDEX_PATH" qmd status`.

If more than 10 files were removed, warn: "Large prune — verify the vault is intact before relying on semantic search."
