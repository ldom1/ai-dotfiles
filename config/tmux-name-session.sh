#!/usr/bin/env sh
# after-new-session hook: a session created without -s gets a number as its name (tmux default).
# Rename it after its folder (main for ~), with a -2, -3... suffix when the name is taken.
name="$1" dir="$2"
case "$name" in ''|*[!0-9]*) exit 0 ;; esac
if [ "$dir" = "$HOME" ]; then base=main; else base=$(basename "$dir" | tr '.:' '__'); fi
new=$base i=2
while tmux has-session -t "=$new" 2>/dev/null; do new="$base-$i"; i=$((i + 1)); done
tmux rename-session -t "=$name" "$new"
