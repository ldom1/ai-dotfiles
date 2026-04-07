# brain-sync — Edge Cases

Detailed failure scenarios for `scripts/sync.sh`.

## Session start failures

### Dirty working tree

`sync.sh start` detects a dirty tree before pulling:

1. `git stash push -m "brain-sync: pre-pull stash <timestamp>"`
2. `git pull --rebase`
3. `git stash pop`

If stash pop conflicts: warn the user — changes are in `git stash list`, not lost.

### Rebase conflict after pull

Detection: `REBASE_HEAD` exists OR `.git/rebase-merge/` OR `.git/rebase-apply/` directory is present.

Action:
1. `git rebase --abort`
2. Restore stash if one was made
3. Print: `[brain-sync] ERROR: rebase conflict detected. Brain is at its last clean state. ACTION REQUIRED: resolve conflicts in $BRAIN_PATH manually.`

The session continues normally — do not block the user.

### Pull failed (not a rebase conflict)

Causes: network unreachable, SSH key missing, `.git/` permission error, remote URL wrong.

Action:
1. Restore stash if one was made
2. Print: `[brain-sync] ERROR: git pull failed (network, permissions on .git, or remote). Fix access to $BRAIN_PATH or run git pull manually, then retry.`

Do **not** label this as a rebase conflict.

### No remote configured

`git remote` returns nothing.

Action: skip pull entirely, print `[brain-sync] WARNING: no remote configured, skipping pull.`

### Script not found

If the hook cannot locate `sync.sh` (e.g. DOTFILES path wrong).

Action: warn once, do not abort the session.

### No config file

Script cannot find `brain.env` or `BRAIN_ENV_FILE`.

Action: exit 1 with hint listing all three lookup paths.

---

## Session end failures

### Nothing to commit

`git diff` + `git diff --cached` + untracked files all empty.

Action: skip `git commit`, then attempt `git push` for any commits that exist locally but haven't been pushed yet.

### Push rejected or no network

Action: warn the user:

> brain-sync: push failed — your changes are committed locally. Run `git push` in `$BRAIN_PATH` when back online.

Do not exit non-zero to the hook — the commit is safe.

### No remote configured

Action: skip push silently.

---

## Stash management

`sync.sh` uses `git stash push -m "brain-sync: ..."` with a timestamped message. On `stash pop` conflict, the stash entry remains in `git stash list` — the user can recover with `git stash show -p stash@{0}`.
