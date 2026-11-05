#!/usr/bin/env bats
# config/tmux-sidebar.sh : une seule sidebar pour tout le serveur, déplacée dans la fenêtre active,
# masquage, hooks, touches d'écran.
# Serveur tmux dédié (-L aif-test), HOME temporaire, faux aif-sidebar (un `cat` qui affiche
# les touches reçues). Lancer : npx --yes bats@1.13.0 tests/

bats_require_minimum_version 1.5.0
REPO="$BATS_TEST_DIRNAME/.."

setup() {
  export HOME="$BATS_TEST_TMPDIR/home"
  mkdir -p "$HOME/.tmux/plugins/tpm" "$HOME/.local/bin" "$BATS_TEST_TMPDIR/bin"
  ln -s "$(cd "$REPO" && pwd)" "$HOME/ai-dotfiles"
  ln -s "$HOME/ai-dotfiles/config/tmux.conf" "$HOME/.tmux.conf"
  printf '#!/bin/sh\n' > "$HOME/.tmux/plugins/tpm/tpm"
  printf '#!/bin/sh\nexec cat\n' > "$HOME/.local/bin/aif-sidebar"
  printf '#!/bin/sh\nexec %s -L aif-test "$@"\n' "$(command -v tmux)" > "$BATS_TEST_TMPDIR/bin/tmux"
  chmod +x "$HOME/.tmux/plugins/tpm/tpm" "$HOME/.local/bin/aif-sidebar" "$BATS_TEST_TMPDIR/bin/tmux"
  export PATH="$BATS_TEST_TMPDIR/bin:$PATH" AIF_PLATFORM=linux
  tmux -f "$HOME/.tmux.conf" new-session -d -s work -x 200 -y 50
  SB="sh $HOME/ai-dotfiles/config/tmux-sidebar.sh"
}

teardown() { tmux -L aif-test kill-server 2>/dev/null || true; }   # -L explicite : setup a pu sauter (skip) avant le wrapper

# sidebars [cible] : nombre de panes sidebar (toute la session par défaut)
sidebars() { tmux list-panes -s -t "${1:-work}" -F '#{@aif_sidebar}' | grep -c '^1$' || true; }
# sidebar_at : fenêtre et PID de l'unique sidebar du serveur
sidebar_at() { tmux list-panes -a -F '#{@aif_sidebar} #{window_id} #{pane_pid}' | awk '$1 == 1 { print $2, $3 }'; }
wait_sidebars() { for _ in $(seq 1 25); do [ "$(sidebars "${2:-work}")" -eq "$1" ] && return 0; sleep 0.2; done; sidebars >&3; return 1; }

@test "ensure opens one sidebar on the left of the window, never two" {
  $SB ensure
  $SB ensure
  [ "$(sidebars)" -eq 1 ]
  [ "$(tmux list-panes -t work -F '#{pane_left} #{@aif_sidebar}' | sort -n | head -1)" = "0 1" ]
  [ "$(tmux list-panes -t work -F '#{pane_width} #{@aif_sidebar}' | awk '$2 == 1 { print $1 }')" -eq 44 ]
}

@test "the sidebar keeps its width when the window is resized" {
  $SB ensure
  tmux set -g window-size manual
  tmux resize-window -t work -x 120 -y 40
  tmux resize-window -t work -x 220 -y 40
  $SB ensure   # en vrai : hook client-resized (aucun client attaché dans ce test)
  w() { tmux list-panes -t work -F '#{pane_width} #{@aif_sidebar}' | awk '$2 == 1 { print $1 }'; }
  for _ in $(seq 1 25); do [ "$(w)" -eq 44 ] && break; sleep 0.2; done
  [ "$(w)" -eq 44 ]
}

@test "hooks at the same time still give one sidebar (lock)" {
  $SB ensure & $SB ensure & $SB ensure & wait
  [ "$(sidebars)" -eq 1 ]
}

@test "a new window gets the sidebar from the after-new-window hook: moved, not a second one" {
  $SB ensure
  pid=$(sidebar_at | cut -d' ' -f2)
  tmux new-window -t work
  win=$(tmux display -p -t work '#{window_id}')
  for _ in $(seq 1 25); do [ "$(sidebar_at)" = "$win $pid" ] && break; sleep 0.2; done
  [ "$(sidebar_at)" = "$win $pid" ]
  [ "$(sidebars)" -eq 1 ]
}

@test "switching session moves the same sidebar process, at its width, focus unchanged" {
  $SB ensure
  pid=$(sidebar_at | cut -d' ' -f2)
  tmux new-session -d -s other -x 200 -y 50
  win=$(tmux display -p -t other: '#{window_id}')
  work=$(tmux display -p -t other: '#{pane_id}')
  $SB ensure "$win"
  [ "$(sidebar_at)" = "$win $pid" ]
  [ "$(sidebars work)" -eq 0 ] && [ "$(sidebars other)" -eq 1 ]
  [ "$(tmux list-panes -t other: -F '#{pane_width} #{@aif_sidebar}' | awk '$2 == 1 { print $1 }')" -eq 44 ]
  [ "$(tmux display -p -t other: '#{pane_id}')" = "$work" ]
  [ "$(tmux list-panes -t other: -F '#{pane_left} #{@aif_sidebar}' | sort -n | head -1)" = "0 1" ]
}

@test "toggle hides every sidebar, then shows it again in the current window" {
  $SB ensure
  tmux new-window -t work
  win=$(tmux display -p -t work '#{window_id}')
  for _ in $(seq 1 25); do [ "$(sidebar_at | cut -d' ' -f1)" = "$win" ] && break; sleep 0.2; done
  $SB toggle
  [ "$(sidebars)" -eq 0 ] && [ "$(tmux show -gv @aif-sidebar)" = off ]
  $SB ensure
  [ "$(sidebars)" -eq 0 ]
  $SB toggle
  [ "$(sidebars)" -eq 1 ]
}

@test "screen K shows a hidden sidebar, focuses it and sends K" {
  $SB toggle
  $SB screen K
  [ "$(sidebars)" -eq 1 ]
  [ "$(tmux display -p -t work '#{@aif_sidebar}')" = 1 ]
  for _ in $(seq 1 25); do tmux capture-pane -p -t work | grep -q K && break; sleep 0.2; done
  tmux capture-pane -p -t work | grep -q K
}

@test "splits do nothing in the sidebar pane" {
  $SB focus
  tmux aif-split-right
  [ "$(tmux list-panes -t work | wc -l)" -eq 2 ]
}

@test "resurrect save file: the sidebar pane is dropped" {
  printf 'pane\twork\t1\t1\t:*\t1\tt\t:/x\t1\taif-sidebar\t:\npane\twork\t1\t1\t:\t2\tt\t:/x\t0\tzsh\t:\n' > "$BATS_TEST_TMPDIR/save.txt"
  sh "$REPO/config/tmux-resurrect-sidebar.sh" save "$BATS_TEST_TMPDIR/save.txt"
  [ "$(grep -c '' "$BATS_TEST_TMPDIR/save.txt")" -eq 1 ] && grep -q zsh "$BATS_TEST_TMPDIR/save.txt"
}
