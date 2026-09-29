# brain-sync — Edge Cases

Failure behaviour of `scripts/sync.sh`. Messages are printed to stderr; the hooks append them to `~/ai-dotfiles/.claude/logs/brain-load.log` (start) and `~/.claude/logs/brain-sync-end.log` (end) and ignore the exit code, so no failure blocks the session.

## start (per repo: vault, then ai-dotfiles)

| Situation | Behaviour |
|---|---|
| Not a git repo (ai-dotfiles) | Skip. For the vault, `sync.sh` exits 1 before doing anything. |
| No remote | Skip pull, warn. |
| Tracked changes | `git stash push -m "brain-sync: pre-pull stash <ts>"` → pull → `git stash pop`. Untracked files are not stashed and not touched by the rebase. |
| Pull fails, no rebase state | Retry twice after 3 s (transient `index.lock` on `/mnt/c`), then pop the stash and print `git pull failed after 3 attempts`. Cause is network, SSH key or `.git` permissions — not a conflict. |
| Rebase conflict (`REBASE_HEAD`, `.git/rebase-merge/` or `.git/rebase-apply/`) | `git rebase --abort`, pop stash, report failure. The vault stays at its last local state; resolve by hand in `$BRAIN_PATH`. |
| Stash pop conflicts | Warn; the changes stay in `git stash list` — recover with `git stash show -p stash@{0}`. |
| No config file | Exit 1, listing the three lookup paths (`$BRAIN_ENV_FILE`, `brain.env` beside the script, `config/brain.env`). |

## end (vault only)

| Situation | Behaviour |
|---|---|
| Nothing to commit | Skip commit, still push unpushed commits. |
| No remote | Skip push. |
| Push rejected / offline | Print `push failed … your commit is local`, return 1. Under `set -e` this ends the script, so the QMD reindex is skipped for that session; run `git push` in `$BRAIN_PATH` when back online. |
| `qmd` missing or `QMD_INDEX_PATH` unset | Reindex skipped silently. |
| `qmd embed` without GPU | Falls back to CPU (Vulkan build error in the log is expected); slow but completes. |
