#!/usr/bin/env bash
# Statusline harness check: hook scripts in settings.json are executable, vault has no unpushed commits.
bad=$(jq -r '.hooks[][].hooks[].command' "$HOME/.claude/settings.json" 2>/dev/null \
  | awk '{print $1}' | sort -u | while read -r c; do [[ -x $c ]] || echo x; done | wc -l)
BRAIN_PATH=$(sed -n 's/^BRAIN_PATH="\{0,1\}\([^"]*\)"\{0,1\}$/\1/p' "$HOME/ai-dotfiles/config/brain.env" 2>/dev/null)
ahead=$(git -C "$BRAIN_PATH" rev-list --count '@{u}..HEAD' 2>/dev/null || echo "?")

out=""
(( bad > 0 )) && out+="✗ ${bad} hooks missing "
[[ $ahead != 0 ]] && out+="✗ vault ↑${ahead} "
if [[ -n $out ]]; then printf '\033[31m%s\033[0m\n' "${out% }"; else printf '\033[32m✓ harness\033[0m\n'; fi
