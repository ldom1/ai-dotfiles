#!/usr/bin/env sh
# tmux-resurrect hooks for the opensessions sidebar.
#   save <file>  (post-save-layout): drop sidebar panes; restored, they come back as empty shells.
#   restore      (post-restore-all): opensessions may spawn a 2nd sidebar during the restore; keep one per window.
case "$1" in
  save)
    awk -F'\t' '!($1 == "pane" && $10 == "opensessions-sidebar")' "$2" > "$2.tmp" && mv "$2.tmp" "$2" ;;
  restore)
    sleep 2
    tmux list-panes -a -F '#{window_id} #{pane_id} #{pane_current_command}' |
      awk '$3 == "opensessions-sidebar" && seen[$1]++ { print $2 }' |
      while read -r pane; do tmux kill-pane -t "$pane"; done ;;
esac
