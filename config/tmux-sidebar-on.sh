#!/usr/bin/env sh
# Show the opensessions sidebar unless one is already open (it starts hidden on each tmux server).
tmux list-panes -a -F '#{pane_current_command}' | grep -q opensessions-sidebar ||
  sh ~/.tmux/plugins/opensessions/integrations/tmux-plugin/scripts/toggle.sh
