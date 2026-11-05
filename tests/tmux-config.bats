#!/usr/bin/env bats
# config/tmux.conf se charge sans erreur, sur chaque plateforme, avec la version de tmux installée
# (3.2a en WSL Ubuntu 22.04, 3.6a en Ubuntu 26.04). Serveur dédié (-L aif-test), HOME temporaire :
# les plugins TPM ne sont pas chargés (un vrai opensessions toucherait au serveur en cours).
# Lancer : npx --yes bats@1.13.0 tests/

bats_require_minimum_version 1.5.0
REPO="$BATS_TEST_DIRNAME/.."

setup() {
  export HOME="$BATS_TEST_TMPDIR/home"
  mkdir -p "$HOME/.tmux/plugins/tpm"
  ln -s "$(cd "$REPO" && pwd)" "$HOME/ai-dotfiles"
  ln -s "$HOME/ai-dotfiles/config/tmux.conf" "$HOME/.tmux.conf"
  printf '#!/bin/sh\n' > "$HOME/.tmux/plugins/tpm/tpm" && chmod +x "$HOME/.tmux/plugins/tpm/tpm"
}

teardown() { tmux -L aif-test kill-server 2>/dev/null || true; }

t() { tmux -L aif-test "$@"; }
# Commande liée à une touche (les alias aif-* sont développés au bind)
cmd() { t list-keys -T "$1" "$2" | sed -E 's/^bind-key +(-r +)?-T +[^ ]+ +[^ ]+ +//'; }

# Démarre le serveur pour la plateforme $1, puis recharge la config : source-file sort en
# erreur et écrit sur stderr à la moindre ligne refusée par cette version de tmux.
start() {
  AIF_PLATFORM=$1 t -f "$HOME/.tmux.conf" new-session -d
  run t source-file "$HOME/.tmux.conf"
  echo "tmux $(t display -p '#{version}'): $output"
  [ "$status" -eq 0 ] && [ -z "$output" ]
}

# Le fichier plateforme est chargé via run-shell, qui avale ses erreurs : le relire à part,
# après les vérifications (le relire avant masquerait un chargement manquant).
platform_parses() {
  run t source-file "$HOME/ai-dotfiles/config/tmux-platform-$1.conf"
  [ "$status" -eq 0 ] && [ -z "$output" ]
}

@test "wsl: config loads, Windows Terminal user-keys reach the actions" {
  start wsl
  for k in o:0 e:1 x:2 n:3 b:4 k:5; do
    [ -n "$(cmd root "S-C-${k%:*}")" ]
    [ "$(cmd root "User${k#*:}")" = "$(cmd root "S-C-${k%:*}")" ]
  done
  [[ "$(cmd root User0)" == *"split-window -h"* ]]
  [ -z "$(t show -sv copy-command)" ]
  platform_parses wsl
}

@test "linux: config loads, the selection goes to aif-platform copy" {
  start linux
  [ "$(t show -sv copy-command)" = "$HOME/ai-dotfiles/bin/aif-platform copy" ]   # tmux développe ~
  run -1 sh -c "tmux -L aif-test list-keys -T root | grep -q User0"
  t show -s terminal-features | grep -q 'xterm-ghostty:RGB:extkeys:clipboard'
  platform_parses linux
}

@test "prefix keys: O E N X B Q Tab and / are bound" {
  start linux
  [[ "$(cmd root S-C-x)" == *kill-pane* ]]
  [[ "$(cmd prefix X)" == *"tmux-sidebar.sh screen K"* ]]
  [ "$(cmd root S-C-k)" = "$(cmd prefix X)" ]
  for k in o:O e:E n:N b:B; do [ "$(cmd prefix "${k#*:}")" = "$(cmd root "S-C-${k%:*}")" ]; done
  [[ "$(cmd prefix Q)" == *"tmux-sidebar.sh screen Q"* ]]
  [ "$(cmd prefix Tab)" = "switch-client -l" ]
  t show-hooks -g | grep -q 'client-resized.*tmux-sidebar.sh ensure' 
  t show -gv status-right | grep -qF "#(~/.local/bin/aif-agents status '#{pane_current_path}')"
  [ "$(cmd prefix /)" = "list-keys -N" ]
  [[ "$(cmd prefix '?')" == *"aif-sidebar help"* ]]
}

@test "mouse selection copies and says so" {
  start wsl
  for k in MouseDragEnd1Pane DoubleClick1Pane y; do
    [[ "$(cmd copy-mode-vi "$k")" == *'copy-pipe-and-cancel \; display-message -d 1500 "Copied to clipboard"'* ]]
  done
}

@test "csi-u key format only from tmux 3.5" {
  start linux
  if t display -p '#{>=:#{version},3.5}' | grep -q 1; then
    [ "$(t show -sv extended-keys-format)" = csi-u ]
  else
    run -1 tmux -L aif-test show -sv extended-keys-format
  fi
}

@test "Ctrl+Shift+X action closes the current pane, not the session" {
  start linux
  t split-window -d
  [ "$(t list-panes | wc -l)" -eq 2 ]
  t aif-kill-pane
  [ "$(t list-panes | wc -l)" -eq 1 ]
  [ "$(t list-sessions | wc -l)" -eq 1 ]
}
