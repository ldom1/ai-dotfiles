#!/usr/bin/env sh
# Ring every attached client: tmux sends a bell only to clients of the session that rang,
# so an agent waiting in a background session would flash nothing (alert-bell hook).
tmux list-clients -F '#{client_tty}' | while read -r tty; do printf '\a' > "$tty"; done
