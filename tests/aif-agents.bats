#!/usr/bin/env bats
# bin/aif-agents list --json sur un serveur tmux dédié (-L aif-test) : session, état final
# (stale, unknown, error calculés à la lecture), ordre et jump, stats git.
# Lancer : npx --yes bats@1.13.0 tests/

bats_require_minimum_version 1.5.0
REPO="$BATS_TEST_DIRNAME/.."

setup() {
  export AIF_STATE_DIR="$BATS_TEST_TMPDIR/agents"
  mkdir -p "$AIF_STATE_DIR" "$BATS_TEST_TMPDIR/bin"
  printf '#!/bin/sh\nexec %s -L aif-test "$@"\n' "$(command -v tmux)" > "$BATS_TEST_TMPDIR/bin/tmux"
  # Faux agent : ps le voit sous le nom « claude » (nom du script)
  printf '#!/bin/sh\nwhile :; do sleep 1; done\n' > "$BATS_TEST_TMPDIR/bin/claude"
  chmod +x "$BATS_TEST_TMPDIR/bin/"*
  export PATH="$BATS_TEST_TMPDIR/bin:$PATH"
  # Dépôt git avec une modification : +2 −1 sur 1 fichier
  REPO_DIR="$BATS_TEST_TMPDIR/proj"
  git init -q "$REPO_DIR" && printf 'a\nb\n' > "$REPO_DIR/f"
  git -C "$REPO_DIR" add f && git -C "$REPO_DIR" -c user.email=t@t -c user.name=t commit -qm init
  printf 'a\nc\nd\n' > "$REPO_DIR/f"
  tmux -f /dev/null new-session -d -s proj -x 250 -y 120 -c "$REPO_DIR"
}

teardown() { tmux kill-server 2>/dev/null || true; }

# new_pane <commande> : ouvre un pane dans la session proj, affiche son id
new_pane() { tmux split-window -d -P -F '#{pane_id}' -t proj -c "$REPO_DIR" "$@"; tmux select-layout -t proj tiled >/dev/null; }
# put <pane> <state> <âge en s> : écrit un fichier d'état comme aif-agent-hook
put() {
  jq -n --arg p "$1" --arg s "$2" --argjson t "$(( $(date +%s) - $3 ))" --arg cwd "$REPO_DIR" \
    '{pane: $p, state: $s, cwd: $cwd, task: "t", updated_at: $t, started_at: $t}' > "$AIF_STATE_DIR/${1#%}.json"
}
list() { "$REPO/bin/aif-agents" list --json; }
wait_claude() { for _ in 1 2 3 4 5 6 7 8 9 10; do ps -e -o comm= | grep -qx claude && return; sleep 0.2; done; }

@test "final states, priority order and jump numbers" {
  running=$(new_pane claude); check=$(new_pane claude); stale=$(new_pane claude)
  oldcheck=$(new_pane claude); unknown=$(new_pane claude); gone=$(new_pane)
  wait_claude
  put "$running" running 5; put "$check" check 5; put "$stale" running 7200
  put "$oldcheck" check 7200; put "$gone" done 5; put %999 running 5   # %999 : pane absent
  run -0 list
  echo "$output" | jq -c '.[] | [.pane, .state, .jump]'
  [ "$(jq -r 'map(.pane) | index("%999")' <<<"$output")" = null ]
  [ "$(jq -r --arg p "$check" '.[] | select(.pane == $p) | .state' <<<"$output")" = check ]
  [ "$(jq -r --arg p "$oldcheck" '.[] | select(.pane == $p) | .state' <<<"$output")" = check ]
  [ "$(jq -r --arg p "$stale" '.[] | select(.pane == $p) | .state' <<<"$output")" = stale ]
  [ "$(jq -r --arg p "$unknown" '.[] | select(.pane == $p) | .state' <<<"$output")" = unknown ]
  [ "$(jq -r --arg p "$gone" '.[] | select(.pane == $p) | .state + " " + .error' <<<"$output")" = "error agent exited" ]
  [ "$(jq -r 'map(.state) | join(",")' <<<"$output")" = "check,check,error,running,unknown,stale" ]
  [ "$(jq -r 'map(.jump) | join(",")' <<<"$output")" = "1,2,3,4,5,6" ]
  [ "$(jq -r 'map(.session) | unique | join(",")' <<<"$output")" = proj ]
}

@test "AIF_STALE_AFTER sets the stale threshold" {
  p=$(new_pane claude); wait_claude
  put "$p" running 120
  [ "$(list | jq -r '.[0].state')" = running ]
  [ "$(AIF_STALE_AFTER=60 "$REPO/bin/aif-agents" list --json | jq -r '.[0].state')" = stale ]
}

@test "git stats from git diff --numstat HEAD, cached 5 s" {
  p=$(new_pane claude); wait_claude
  put "$p" running 1
  [ "$(list | jq -c '.[0].git')" = '{"add":2,"del":1,"files":1}' ]
  printf 'x\n' >> "$REPO_DIR/f"
  [ "$(list | jq -c '.[0].git')" = '{"add":2,"del":1,"files":1}' ]
  sleep 5
  [ "$(list | jq -c '.[0].git')" = '{"add":3,"del":1,"files":1}' ]
}

@test "only the 9 first agents get a jump number" {
  for _ in $(seq 1 10); do put "$(new_pane claude)" running 1; done
  wait_claude
  run -0 list
  [ "$(jq length <<<"$output")" -eq 10 ]
  [ "$(jq -r '.[8].jump, .[9].jump' <<<"$output" | tr '\n' ' ')" = "9 null " ]
}

@test "no tmux server: empty list, exit 0" {
  tmux kill-server
  run -0 list
  [ "$output" = "[]" ]
}

@test "diff: files with +/- counts and the first hunk, from the agent folder" {
  p=$(new_pane claude); wait_claude
  put "$p" running 1
  printf 'new\n' > "$REPO_DIR/g" && git -C "$REPO_DIR" add g
  run -0 "$REPO/bin/aif-agents" diff "$p" --json
  [ "$(jq -c '.files' <<<"$output")" = '[{"file":"f","add":2,"del":1},{"file":"g","add":1,"del":0}]' ]
  [ "$(jq -r '.hunk' <<<"$output" | head -1)" = "@@ -1,2 +1,3 @@" ]
  [ "$(jq -r '.hunk' <<<"$output" | grep -c '^[+-]')" -eq 3 ]
  ! jq -r '.hunk' <<<"$output" | grep -q '^+new'
}

@test "diff: unknown pane fails with a message" {
  run "$REPO/bin/aif-agents" diff %999 --json
  [ "$status" -ne 0 ]
}
