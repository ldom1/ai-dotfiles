#!/usr/bin/env bats
# .claude/hooks/fails-on-base.sh : sur un commit de fix, les tests modifiés doivent échouer sur la base.
# Chaque test construit son dépôt git dans $BATS_TEST_TMPDIR. TEST_CMD est un runner POSIX sh
# (chaque fichier de test est un script sh) : ni pytest ni environnement Python requis.
# Lancer : npx --yes bats@1.13.0 tests/fails-on-base.bats

bats_require_minimum_version 1.5.0
SCRIPT="$BATS_TEST_DIRNAME/../.claude/hooks/fails-on-base.sh"

setup() {
  repo="$BATS_TEST_TMPDIR/repo"
  mkdir -p "$repo"
  git -C "$repo" init -q
  git -C "$repo" config user.name t
  git -C "$repo" config user.email t@t
  # base : m.sh définit f, qui rend 0
  printf 'f() { echo 0; }\n' > "$repo/m.sh"
  git -C "$repo" add -A
  git -C "$repo" commit -q -m base
  # runner hors dépôt : lance chaque fichier de test avec sh, échoue au premier échec
  printf '#!/bin/sh\nfor f; do sh "$f" || exit 1; done\n' > "$BATS_TEST_TMPDIR/run.sh"
  chmod +x "$BATS_TEST_TMPDIR/run.sh"
  export TEST_CMD="$BATS_TEST_TMPDIR/run.sh"
}

# commit_fix <corps du test> : m.sh rend 3, m_test.sh source m.sh puis exécute <corps>
commit_fix() {
  printf 'f() { echo 3; }\n' > "$repo/m.sh"
  printf '. ./m.sh\n%s\n' "$1" > "$repo/m_test.sh"
  git -C "$repo" add -A
  git -C "$repo" commit -q -m fix
}

# lance le script dans le dépôt ; stderr dans $stderr
run_fob() {
  run --separate-stderr sh -c 'cd "$1" && shift && "$@"' _ "$repo" "$SCRIPT" "$@"
}

one_worktree() { [ "$(git -C "$repo" worktree list | wc -l)" -eq 1 ]; }

@test "fix commit whose test passes on base: exit 1, FAIL on stderr" {
  commit_fix '[ "$(f 1)" -ge 0 ]'
  run_fob
  [ "$status" -eq 1 ]
  [[ "$stderr" == *"FAIL: changed tests pass on base"* ]]
}

@test "fix commit whose test fails on base: exit 0, silent" {
  commit_fix '[ "$(f 1)" = 3 ]'
  run_fob
  [ "$status" -eq 0 ]
  [ -z "$stderr" ]
}

@test "explicit base argument is used" {
  commit_fix '[ "$(f 1)" -ge 0 ]'
  git -C "$repo" commit -q --allow-empty -m noise
  run_fob HEAD~2
  [ "$status" -eq 1 ]
  # HEAD~1 already holds the fix: nothing differs
  run_fob HEAD~1
  [ "$status" -eq 0 ]
}

@test "tests-only change: exit 0, nothing to revert" {
  printf '. ./m.sh\n[ "$(f 1)" -ge 0 ]\n' > "$repo/m_test.sh"
  git -C "$repo" add -A
  git -C "$repo" commit -q -m tests
  run_fob
  [ "$status" -eq 0 ]
}

@test "no test changed: exit 0" {
  printf 'f() { echo 3; }\n' > "$repo/m.sh"
  git -C "$repo" commit -q -am code
  run_fob
  [ "$status" -eq 0 ]
}

@test "a new source file counts as the fix: weak test exits 1" {
  printf 'g() { echo 1; }\n' > "$repo/g.sh"
  printf 'true\n' > "$repo/g_test.sh"
  git -C "$repo" add -A
  git -C "$repo" commit -q -m fix
  run_fob
  [ "$status" -eq 1 ]
}

@test "a new source file counts as the fix: strong test exits 0" {
  printf 'g() { echo 1; }\n' > "$repo/g.sh"
  printf '. ./g.sh\n[ "$(g)" = 1 ]\n' > "$repo/g_test.sh"
  git -C "$repo" add -A
  git -C "$repo" commit -q -m fix
  run_fob
  [ "$status" -eq 0 ]
}

@test "base fails on a missing module only: exit 1, INCONCLUSIVE" {
  commit_fix 'echo "ModuleNotFoundError: No module named foo" >&2; exit 1'
  run_fob
  [ "$status" -eq 1 ]
  [[ "$stderr" == *"INCONCLUSIVE"* ]]
}

@test "TEST_CMD unset: exit 2 before anything is created" {
  commit_fix '[ "$(f 1)" = 3 ]'
  unset TEST_CMD
  run_fob
  [ "$status" -eq 2 ]
  one_worktree
}

@test "unknown base: exit 2" {
  commit_fix '[ "$(f 1)" = 3 ]'
  run_fob no-such-ref
  [ "$status" -eq 2 ]
  one_worktree
}

@test "worktree removed on every exit path" {
  commit_fix '[ "$(f 1)" = 3 ]'
  run_fob
  [ "$status" -eq 0 ]
  one_worktree
  # tests pass on base: exit 1
  printf 'h() { :; }\n' > "$repo/h.sh"
  printf 'true\n' > "$repo/h_test.sh"
  git -C "$repo" add -A
  git -C "$repo" commit -q -m weak
  run_fob HEAD~1
  [ "$status" -eq 1 ]
  one_worktree
  # TEST_CMD fails on its own (exit 1, no output)
  TEST_CMD=false run_fob HEAD~1
  [ "$status" -eq 0 ]
  one_worktree
}

@test "runs from a subdirectory of the repo" {
  commit_fix '[ "$(f 1)" = 3 ]'
  mkdir "$repo/sub"
  run --separate-stderr sh -c 'cd "$1/sub" && "$2"' _ "$repo" "$SCRIPT"
  [ "$status" -eq 0 ]
  one_worktree
}

@test "HEAD and working tree are untouched" {
  commit_fix '[ "$(f 1)" = 3 ]'
  head=$(git -C "$repo" rev-parse HEAD)
  run_fob
  [ "$(git -C "$repo" rev-parse HEAD)" = "$head" ]
  [ -z "$(git -C "$repo" status --porcelain)" ]
}
