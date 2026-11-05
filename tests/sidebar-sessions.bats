#!/usr/bin/env bats
# Circuit complet sur un serveur tmux dédié (-L aif-test) : config/tmux.conf, tmux-sidebar.sh et le
# vrai aif-sidebar. Écrans New session et Kill session, renommage, onglets SESSIONS et ACTIONS.
# HOME temporaire : dossiers proposés = dépôts git sous ~ ; tmux-resurrect remplacé par un faux
# save.sh qui laisse une trace. Binaire : le plus récent de sidebar/target/{release,debug}.

bats_require_minimum_version 1.5.0
REPO="$BATS_TEST_DIRNAME/.."

setup() {
  BIN=${AIF_SIDEBAR_BIN:-$(ls -t "$REPO"/sidebar/target/{release,debug}/aif-sidebar 2>/dev/null | head -1)}
  [ -n "$BIN" ] || skip "aif-sidebar not built"
  command -v zoxide >/dev/null && skip "zoxide installed: folders would come from it"
  export HOME="$BATS_TEST_TMPDIR/home" AIF_PLATFORM=linux AIF_STATE_DIR="$BATS_TEST_TMPDIR/agents"
  R="$HOME/.tmux/plugins/tmux-resurrect/scripts"
  mkdir -p "$HOME/.tmux/plugins/tpm" "$HOME/.local/bin" "$BATS_TEST_TMPDIR/bin" "$R" "$AIF_STATE_DIR" \
    "$HOME/dev/web/.git" "$HOME/dev/api/.git" "$HOME/other/api/.git"
  ln -s "$(cd "$REPO" && pwd)" "$HOME/ai-dotfiles"
  ln -s "$HOME/ai-dotfiles/config/tmux.conf" "$HOME/.tmux.conf"
  ln -s "$BIN" "$HOME/.local/bin/aif-sidebar"
  ln -s "$REPO/bin/aif-agents" "$BATS_TEST_TMPDIR/bin/aif-agents"
  printf '#!/bin/sh\n' > "$HOME/.tmux/plugins/tpm/tpm"
  printf '#!/bin/sh\nd="$HOME/.local/share/tmux/resurrect"; mkdir -p "$d"; touch "$d/last" "$HOME/saved"\n' > "$R/save.sh"
  printf '#!/bin/sh\nexec %s -L aif-test "$@"\n' "$(command -v tmux)" > "$BATS_TEST_TMPDIR/bin/tmux"
  chmod +x "$HOME/.tmux/plugins/tpm/tpm" "$R/save.sh" "$BATS_TEST_TMPDIR/bin/tmux"
  export PATH="$BATS_TEST_TMPDIR/bin:$PATH" AIF_DOTFILES="$REPO"
  # main en dernier : sans client attaché, tmux prend la session la plus récente comme courante
  tmux -f "$HOME/.tmux.conf" new-session -d -s api -c "$HOME/dev/api"
  tmux new-session -d -s main -x 200 -y 50 -c "$HOME"
  sh "$HOME/ai-dotfiles/config/tmux-sidebar.sh" ensure "$(tmux display -p -t main '#{window_id}')"
  SB=$(tmux list-panes -t main -F '#{pane_id} #{@aif_sidebar}' | awk '$2 == 1 { print $1 }')
  [ -n "$SB" ]
}

teardown() { tmux -L aif-test kill-server 2>/dev/null || true; }   # -L explicite : setup a pu sauter (skip) avant le wrapper

screen() {
  for _ in $(seq 1 25); do tmux capture-pane -p -t "$SB" | grep -qF -- "$1" && return 0; sleep 0.2; done
  tmux capture-pane -p -t "$SB" >&3; return 1
}
has() { for _ in $(seq 1 25); do tmux has-session -t "=$1" 2>/dev/null && return 0; sleep 0.2; done; return 1; }
gone() { for _ in $(seq 1 25); do tmux has-session -t "=$1" 2>/dev/null || return 0; sleep 0.2; done; return 1; }

@test "Ctrl+Shift+N action opens the New session screen; a free name creates the session" {
  tmux aif-new-session
  screen "NEW SESSION"
  screen "~/dev/api"
  screen "attach api"
  screen "name taken → api-2"
  tmux send-keys -t "$SB" -l web
  screen "~/dev/web"
  tmux send-keys -t "$SB" Enter
  has web
  [ "$(tmux display -p -t =web: '#{session_path}')" = "$HOME/dev/web" ]
}

@test "a taken name gets -2" {
  tmux aif-new-session
  screen "name taken → api-2"
  tmux send-keys -t "$SB" -l other
  screen "~/other/api"
  tmux send-keys -t "$SB" Enter
  has api-2
}

@test "Kill session screen targets the current session, not the cursor; saves, then kills it" {
  tmux aif-new-session; screen "NEW SESSION"
  tmux send-keys -t "$SB" Escape
  tmux send-keys -t "$SB" Tab; tmux send-keys -t "$SB" Tab   # AGENTS → ACTIONS → SESSIONS
  screen "▸ 02 main"
  tmux send-keys -t "$SB" Up                                  # curseur sur api
  tmux send-keys -t "$SB" K
  screen "KILL SESSION main"                                  # la session courante, pas le curseur
  screen "No agents in this session."
  tmux send-keys -t "$SB" Enter
  gone main
  has api
  [ -f "$HOME/saved" ]
}

@test "rename from the SESSIONS tab" {
  tmux send-keys -t "$SB" BTab                                # AGENTS → SESSIONS
  screen "▸ 02 main"
  tmux send-keys -t "$SB" r
  screen "RENAME SESSION main"
  tmux send-keys -t "$SB" BSpace BSpace BSpace BSpace
  tmux send-keys -t "$SB" -l home
  tmux send-keys -t "$SB" Enter
  has home
}

@test "ACTIONS shows the target session and the last save" {
  tmux send-keys -t "$SB" Tab                                 # AGENTS → ACTIONS
  screen "TARGET main ~"
  screen "no save yet"
  tmux send-keys -t "$SB" s
  screen "last save"
}
