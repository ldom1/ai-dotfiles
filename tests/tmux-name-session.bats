#!/usr/bin/env bats
# Renommage auto (config/tmux-name-session.sh) face à une restauration tmux-resurrect,
# sur un serveur tmux dédié (-L aif-test). Lancer : npx --yes bats@1.13.0 tests/
# Nécessite tmux-resurrect dans ~/.tmux/plugins (installé par TPM).

REPO="$BATS_TEST_DIRNAME/.."
RESURRECT="$HOME/.tmux/plugins/tmux-resurrect"

setup() {
  [ -x "$RESURRECT/scripts/restore.sh" ] || skip "tmux-resurrect not installed"
  export AIF_HOME="$BATS_TEST_TMPDIR/home" PROJ="$BATS_TEST_TMPDIR/proj"
  mkdir -p "$AIF_HOME/resurrect" "$PROJ"
  sed -e "s|@HOME@|$AIF_HOME|" -e "s|@PROJ@|$PROJ|" "$REPO/tests/fixtures/resurrect-main-proj.txt" \
    > "$AIF_HOME/resurrect/save.txt"
  ln -s save.txt "$AIF_HOME/resurrect/last"
  # tmux shim: the hook calls plain `tmux`; keep it on the test server
  mkdir -p "$BATS_TEST_TMPDIR/bin"
  printf '#!/bin/sh\nexec %s -L aif-test "$@"\n' "$(command -v tmux)" > "$BATS_TEST_TMPDIR/bin/tmux"
  chmod +x "$BATS_TEST_TMPDIR/bin/tmux"
  export PATH="$BATS_TEST_TMPDIR/bin:$PATH" HOME="$AIF_HOME"
  cat > "$BATS_TEST_TMPDIR/tmux.conf" <<CONF
set -g @resurrect-dir '$AIF_HOME/resurrect'
set -g @continuum-restore 'on'
set-hook -g after-new-session 'run -b "sh $REPO/config/tmux-name-session.sh \"#{session_name}\" \"#{session_path}\""'
run '$RESURRECT/resurrect.tmux'
CONF
}

teardown() { tmux -L aif-test kill-server 2>/dev/null || true; }   # -L explicite : setup a pu sauter (skip) avant le wrapper

sessions() { tmux list-sessions -F '#{session_name}' | sort | tr '\n' ' '; }

# Démarre le serveur comme `tmux` lancé dans $1, puis restaure comme tmux-continuum (après 1 s).
start_and_restore() {
  (cd "$1" && tmux -f "$BATS_TEST_TMPDIR/tmux.conf" new-session -d)
  start_and_restore_only
}

start_and_restore_only() {
  sleep 1
  tmux run-shell "$RESURRECT/scripts/restore.sh"
  sleep 1
}

@test "restore after a start in ~: no -2 session, no leftover 0" {
  start_and_restore "$AIF_HOME"
  [ "$(sessions)" = "main proj " ]
}

@test "restore after a start in a saved project: no -2 session" {
  start_and_restore "$PROJ"
  [ "$(sessions)" = "main proj " ]
}

@test "restore with a second pane already open (sidebar on attach): no -2 session" {
  (cd "$AIF_HOME" && tmux -f "$BATS_TEST_TMPDIR/tmux.conf" new-session -d)
  tmux split-window -h
  start_and_restore_only
  [ "$(sessions)" = "main proj " ]
}

@test "without a save file, a plain tmux session is named after its folder" {
  rm "$AIF_HOME/resurrect/last"
  (cd "$PROJ" && tmux -f "$BATS_TEST_TMPDIR/tmux.conf" new-session -d)
  sleep 1
  [ "$(sessions)" = "proj " ]
}

@test "a second plain session in a taken folder gets -2" {
  rm "$AIF_HOME/resurrect/last"
  (cd "$PROJ" && tmux -f "$BATS_TEST_TMPDIR/tmux.conf" new-session -d)
  sleep 1
  (cd "$PROJ" && tmux new-session -d)
  sleep 1
  [ "$(sessions)" = "proj proj-2 " ]
}
