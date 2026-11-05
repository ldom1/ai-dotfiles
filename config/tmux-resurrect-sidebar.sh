#!/usr/bin/env sh
# tmux-resurrect hook (post-save-layout) : retire la sidebar du fichier de sauvegarde.
# Restaurée, elle reviendrait comme un shell vide ; tmux-sidebar.sh la rouvre à la place.
#   save <fichier>
case "$1" in
  save) awk -F'\t' '!($1 == "pane" && $10 == "aif-sidebar")' "$2" > "$2.tmp" && mv "$2.tmp" "$2" ;;
esac
