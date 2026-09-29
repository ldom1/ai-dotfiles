---
name: git-promotion
description: >
  Promote code between a repo's stage branches (develop → preprod → main, develop → main, or
  a PR straight onto main when there is no preprod) with a semver tag and a GitHub Release —
  fast-forward only between stages, squash-merge for a PR, never a hand-made merge commit.
  Use whenever the user asks to promote, release, ship, deploy, publish, "push to
  preprod/main", merge a PR "with tag and release", cut a release, or tag a version. A raw
  git push/merge onto a stage branch skips the gate and the version bookkeeping.
user-invocable: true
---

# git-promotion

`scripts/promote.py` moves code onto a stage branch and tags it. Stage branches never carry
independent content, so a promotion is a fast-forward (or, with a single stage, a squash-merged
PR). History stays usable for bisect, blame and revert, and each promotion can carry a version.

## Setup: `.git-promotion.json` at the repo root

```json
{
  "stages": ["develop", "preprod", "main"],
  "tag_prefix": "",
  "gate": [["uv", "run", "pytest", "-q"], ["uv", "run", "ruff", "check", "."]],
  "changelog": "CHANGELOG.md"
}
```

| Key | Meaning |
|---|---|
| `stages` | Branches in promotion order. The last one is the release branch. |
| `tag_prefix` | `"v"` → `v0.7.0`; `""` → `0.7.0`. Match the repo's existing tags. |
| `gate` | Commands run before `--execute` acts; any failure aborts. Optional. |
| `changelog` | If set, the release needs a `## [X.Y.Z]` section in this file at the promoted commit; that section becomes the release notes. Otherwise the notes list the commit subjects. |

Stage shapes:

- `["develop", "preprod", "main"]`: `preprod` is fast-forwarded from `develop` and gets alpha
  tags (`0.3.0a1`); `main` is fast-forwarded from `preprod` and gets the final `0.3.0` plus a
  GitHub Release.
- `["develop", "main"]`: no preprod. `main` is fast-forwarded from `develop` and released.
- `["main"]`: no preprod and no integration branch. PRs target `main`; a release is
  `--pr N`: squash-merge the PR (`gh pr merge --squash --delete-branch`), tag the merge
  commit, create the release.

If a repo has no config, ask the user for its stages before writing one.

## How to promote

```bash
P=~/.claude/skills/git-promotion/scripts/promote.py
python3 $P preprod                # dry run: what would move, which version
python3 $P main --execute         # gate, then atomic tag + branch push, then release
python3 $P main --pr 19           # single stage: dry run for PR 19
python3 $P main --pr 19 --execute
```

Always run the dry run first and read it. It prints the commit or PR that would move and the
version it would get, and exits 1 on anything wrong. It does not run the gate.

**Single-stage PR release, in order:**
1. Dry run `--pr N` → note the version, e.g. `v0.7.0`.
2. If `changelog` is set: on the PR branch, rename `## [Unreleased]` to `## [0.7.0] - YYYY-MM-DD`
   and add an empty `## [Unreleased]` above it. Commit it with `/git-commit`
   (`doc(docs): cut CHANGELOG [Unreleased] into 0.7.0`) and push.
3. `--pr N --execute`. It merges only if the PR head is still the commit that was checked
   (`--match-head-commit`). It runs `gh` with `--repo`, so the local checkout is not
   switched and the local branch is not deleted.

If the release step fails after the tag is pushed, the script exits 4 and prints the
`gh release create` command to run. If a PR is merged but untagged, re-running tags it; if
it is merged and tagged, re-running does nothing.

## Versioning

Semver `X.Y.Z` from `type(scope):` commit types since the last release tag: `fix`/`enh` → patch,
`feat` → minor, `BREAKING CHANGE:` footer or `type!:` → major (minor while `X` is 0).
`doc`/`ci`-only → the branch still moves, with no new tag. A release after an intermediate stage
takes the base of that stage's highest unreleased alpha, the version it already tested.

## What it refuses

- **Target diverged from its source** (exit 1): someone committed directly to the target.
  Never auto-resolved.
- **Gate prerequisites** (exit 1, only when a gate is configured): the source branch (or PR
  head branch) must be checked out, clean, at the remote tip, so the gate tests exactly the
  promoted commit. With no gate, local state is irrelevant and not checked.
- **Gate failure, or a missing CHANGELOG section** (`--execute`, exit 1): nothing is pushed or merged.
- **A PR whose base is not the release branch, or a closed PR** (exit 1).
- **An authorized emergency-hotfix divergence on the release branch** (exit 3): see below.

## Emergency hotfix (multi-stage only)

Use this only when the first stage cannot ship as-is and the fix is production-urgent:
1. Commit the fix directly on the release branch with an `Emergency-Reconciliation: <reason>` footer.
2. Cherry-pick it onto the first stage right away.
3. The next release promotion exits 3, because every diverged commit has the footer and a
   patch-id twin on the first stage. Once the cherry-pick has reached the source stage, reset
   the release branch to the source by hand:
   `git push --force-with-lease=<release>:<old-sha> origin origin/<source>:refs/heads/<release>`.
   Then re-run.

## Never do instead

- `git push origin develop:preprod`, `git merge` into a stage, a merge-commit PR into a stage,
  or `git commit-tree`: these skip the gate and the version bookkeeping.
- `--force` on a stage branch, except the emergency-hotfix reset above.
