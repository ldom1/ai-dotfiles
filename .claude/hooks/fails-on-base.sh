#!/bin/sh
# Rule ^v5: on a fix commit, the changed tests must fail on the base code. Opt-in, not wired by default.
# Usage: TEST_CMD='pytest -q' fails-on-base.sh [base]
# Call it from a repo's .claude/stop-check or git-hooks/pre-push. It runs the changed tests, so keep it
# out of repos with a slow suite.
#
# Exit 0: no test changed, tests only, no fix to revert, or the changed tests fail on base.
# Exit 1: the changed tests pass on base (they cannot detect the fix), or the base run failed on a
#         missing module or command only (inconclusive).
# Exit 2: bad setup (TEST_CMD unset, unknown base, no worktree).
#
# Does NOT catch: fixtures from assumed data, 0-row green steps, a test that fails on base for the wrong
# assertion (only missing-module/command errors are filtered), refactor commits (skip them), watchers,
# ad-hoc shell checks. The clean worktree has no venv or node_modules: link them in before the run if
# the repo needs them, or the run is INCONCLUSIVE.
# Test paths with spaces are not supported.
: "${TEST_CMD:?set TEST_CMD}"
cd "$(git rev-parse --show-toplevel)" || exit 2   # diff paths are relative to the repo root
base=${1:-$(git merge-base HEAD origin/main 2>/dev/null || git rev-parse HEAD~1 2>/dev/null)}
git rev-parse --verify -q "$base^{commit}" >/dev/null || { echo "unknown base: '$base'" >&2; exit 2; }

changed=$(git diff --name-only "$base")
tests=$(git diff --name-only --diff-filter=AM "$base" | grep -E '(^|/)(test_[^/]*\.py|[^/]*_test\.[a-z]+|[^/]*\.test\.[a-z]+)$')
[ -n "$tests" ] || exit 0                                             # no test changed: nothing to prove
printf '%s\n' "$changed" | grep -qvxF "$tests" || exit 0              # tests only: no fix to revert

wt=$(mktemp -d) || exit 2
trap 'git worktree remove --force "$wt" >/dev/null 2>&1; rm -rf "$wt"' EXIT
trap 'exit 130' INT TERM HUP
git worktree add -q --detach "$wt" "$base" || exit 2
for t in $tests; do mkdir -p "$wt/$(dirname "$t")" && cp "$t" "$wt/$t"; done
# shellcheck disable=SC2086  # TEST_CMD and the test paths are meant to word-split
out=$(cd "$wt" && $TEST_CMD $tests 2>&1); rc=$?

if [ $rc -eq 0 ]; then
  echo "FAIL: changed tests pass on base $base: they cannot detect the fix" >&2
  exit 1
fi
if printf '%s\n' "$out" | grep -qE 'ModuleNotFoundError|Cannot find module|command not found|No module named'; then
  echo "INCONCLUSIVE: base run failed on environment, not on the assertion" >&2
  exit 1
fi
exit 0
