#!/usr/bin/env bats
# config/tmux-sidebar.sh : une seule sidebar par fenêtre, masquage, hooks, touches d'écran.
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

teardown() { tmux kill-server 2>/dev/null || true; }

# sidebars [cible] : nombre de panes sidebar (toute la session par défaut)
sidebars() { tmux list-panes -s -t "${1:-work}" -F '#{@aif_sidebar}' | grep -c '^1$' || true; }
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

@test "a new window gets its sidebar from the after-new-window hook" {
  $SB ensure
  tmux new-window -t work
  wait_sidebars 2
}

@test "toggle hides every sidebar, then shows it again in the current window" {
  $SB ensure
  tmux new-window -t work && wait_sidebars 2
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
