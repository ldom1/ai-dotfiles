#!/bin/sh
# Rule ^v5: on a fix commit, the changed tests must fail on the base code. Opt-in, not wired by default.
# Usage: TEST_CMD='pytest -q' fails-on-base.sh [base]
# Call it from a repo's .claude/stop-check or git-hooks/pre-push. It runs the changed tests, so keep it
# out of repos with a slow suite.
#
# A fix is a diff that changes tests (added or modified) and modifies or deletes a non-test file.
# A diff that only adds files is a feature, not a fix: it is skipped (a new module has no pre-fix code).
#
# Each changed test file runs alone on base, so a failing test cannot mask a weak one.
# Exit 0: no test changed, tests only, files added only, or EVERY changed test file fails on base.
# Exit 1: a changed test file passes on base (it cannot detect the fix; each such file is printed), or
#         a base run failed on the environment (rc 126/127, missing module or command): inconclusive.
# Exit 2: bad setup (TEST_CMD unset, unknown base, no worktree).
#
# Does NOT catch: fixtures from assumed data, 0-row green steps, a test that fails on base for the wrong
# assertion (only environment errors are filtered), refactor commits (skip them), watchers, ad-hoc shell
# checks. The clean worktree has no venv or node_modules: link them in before the run if the repo needs
# them, or the run is INCONCLUSIVE.
# Test paths with spaces are not supported.
[ -n "${TEST_CMD:-}" ] || { echo "set TEST_CMD" >&2; exit 2; }
cd "$(git rev-parse --show-toplevel)" || exit 2   # diff paths are relative to the repo root
base=${1:-$(git merge-base HEAD origin/main 2>/dev/null || git rev-parse HEAD~1 2>/dev/null)}
git rev-parse --verify -q "$base^{commit}" >/dev/null || { echo "unknown base: '$base'" >&2; exit 2; }

test_re='(^|/)(test_[^/]*\.py|[^/]*_test\.[a-z]+|[^/]*\.test\.[a-z]+)$'
tests=$(git -c core.quotepath=off diff --name-only --diff-filter=AM "$base" | grep -E "$test_re")
[ -n "$tests" ] || exit 0                    # no test changed: nothing to prove
# no code modified or deleted: no fix to revert
git -c core.quotepath=off diff --name-only --diff-filter=MD "$base" | grep -qvE "$test_re" || exit 0

wt=$(mktemp -d) || exit 2
trap 'git worktree remove --force "$wt" >/dev/null 2>&1; rm -rf "$wt"; git worktree prune' EXIT
trap 'exit 130' INT TERM HUP
git worktree add -q --detach "$wt" "$base" || exit 2
for t in $tests; do mkdir -p "$wt/$(dirname "$t")" && cp "$t" "$wt/$t"; done
# One run per test file: a failing test must not mask a weak one in the same call.
weak=""; env_err=0
for t in $tests; do
  # shellcheck disable=SC2086  # TEST_CMD is meant to word-split
  out=$(cd "$wt" && $TEST_CMD "$t" 2>&1); rc=$?
  # 126/127: the runner did not start. bash says "command not found", dash says "<cmd>: not found".
  if [ $rc -eq 126 ] || [ $rc -eq 127 ] ||
    printf '%s\n' "$out" | grep -qE 'ModuleNotFoundError|Cannot find module|: not found$|No module named'; then
    env_err=1
  elif [ $rc -eq 0 ]; then
    weak="$weak  $t
"
  fi
done

if [ -n "$weak" ]; then
  printf 'FAIL: changed tests pass on base %s: they cannot detect the fix\n%s' "$base" "$weak" >&2
fi
if [ $env_err -eq 1 ]; then
  echo "INCONCLUSIVE: base run failed on environment, not on the assertion" >&2
fi
[ -z "$weak" ] && [ $env_err -eq 0 ]
