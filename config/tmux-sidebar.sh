#!/usr/bin/env sh
# tmux-sidebar.sh — une seule sidebar (aif-sidebar) pour tout le serveur, à gauche de la fenêtre
# active, quand elle est active. Un seul process : onglet, curseur et filtre suivent l'utilisateur
# d'une session à l'autre.
#   ensure [fenêtre]   amène la sidebar dans la fenêtre (join-pane), l'ouvre si elle n'existe pas,
#                      et la remet à sa largeur (hooks tmux, dont client-resized)
#   toggle [fenêtre]   active ou masque la sidebar, dans toutes les fenêtres (Ctrl+Shift+B)
#   focus [fenêtre]    l'affiche si besoin et lui donne le focus (Alt+s)
#   screen <touche> [fenêtre]
#                      l'affiche, lui donne le focus et lui envoie une touche :
#                      N nouvelle session, K tuer la session, Q sauvegarder et quitter
# État : option globale @aif-sidebar (« off » = masquée ; active par défaut).
# Pane de la sidebar : option de pane @aif_sidebar = 1. Largeur : @aif-sidebar-width (défaut 44).
set -u
BIN="$HOME/.local/bin/aif-sidebar"
cmd=${1:-ensure}
[ "$cmd" = screen ] && { key=${2:-}; shift; }
win=${2:-}
[ -n "$win" ] || win=$(tmux display -p '#{window_id}' 2>/dev/null) || exit 0

sidebar_of() { tmux list-panes -t "$1" -F '#{pane_id} #{@aif_sidebar}' 2>/dev/null | awk '$2 == 1 { print $1; exit }'; }
# La sidebar du serveur, dans n'importe quelle fenêtre
any_sidebar() { tmux list-panes -a -F '#{pane_id} #{@aif_sidebar}' 2>/dev/null | awk '$2 == 1 { print $1; exit }'; }

ensure() {
  [ "$(tmux show -gqv @aif-sidebar)" = off ] && return 0
  [ -x "$BIN" ] || return 0
  # Verrou : plusieurs hooks peuvent arriver en même temps (attach + changement de session)
  tmux wait-for -L aif-sidebar
  width=$(tmux show -gqv @aif-sidebar-width); width=${width:-44}
  pane=$(sidebar_of "$win")
  if [ -z "$pane" ] && other=$(any_sidebar) && [ -n "$other" ]; then
    # shortcut: deux clients sur deux sessions se disputent la sidebar, le dernier actif la garde
    tmux join-pane -hbfd -l "$width" -s "$other" -t "$win" 2>/dev/null && pane=$other
  elif [ -z "$pane" ]; then
    pane=$(tmux split-window -hbfd -l "$width" -t "$win" -P -F '#{pane_id}' "$BIN" 2>/dev/null) &&
      tmux set -p -t "$pane" @aif_sidebar 1 && created=1
  elif [ "$(tmux display -p -t "$pane" '#{pane_width}')" != "$width" ]; then
    # tmux redistribue les largeurs quand la fenêtre change de taille : remettre la sidebar à sa largeur
    tmux resize-pane -t "$pane" -x "$width"
  fi
  tmux wait-for -U aif-sidebar
}

show_and_focus() {
  tmux set -g @aif-sidebar on
  ensure
  pane=$(sidebar_of "$win")
  [ -n "$pane" ] && tmux select-pane -t "$pane"
}

case $cmd in
  ensure) ensure ;;
  toggle)
    if [ "$(tmux show -gqv @aif-sidebar)" = off ]; then
      tmux set -g @aif-sidebar on
      ensure
    else
      tmux set -g @aif-sidebar off
      tmux list-panes -a -F '#{pane_id} #{@aif_sidebar}' | awk '$2 == 1 { print $1 }' |
        while read -r p; do tmux kill-pane -t "$p"; done
    fi ;;
  focus) show_and_focus ;;
  screen)
    show_and_focus
    if [ -n "${pane:-}" ]; then
      # Sidebar qui vient de démarrer : lui laisser le temps de lire le clavier
      [ "${created:-0}" = 1 ] && sleep 0.5
      tmux send-keys -t "$pane" "$key"
    else
      # Pas de sidebar (aif-sidebar non installé) : confirmation tmux simple
      save="$HOME/.tmux/plugins/tmux-resurrect/scripts/save.sh quiet"
      case $key in
        K) tmux confirm-before -p "Kill session #S? (y/n)" "run-shell '$save' ; kill-session" ;;
        Q) tmux confirm-before -p "Save all sessions and quit tmux? (y/n)" "run-shell '$save' ; kill-server" ;;
        *) tmux display-message "aif-sidebar is not installed: run install.sh" ;;
      esac
    fi ;;
  *) echo "usage: tmux-sidebar.sh ensure|toggle|focus|screen <key> [window]" >&2; exit 2 ;;
esac
exit 0
