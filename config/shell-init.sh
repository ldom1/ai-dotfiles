# shellcheck shell=sh
# ai-dotfiles : initialisation du terminal. ~/.zshrc et ~/.bashrc la sourcent (ligne ajoutée par
# scripts/install.sh, à la fin du fichier).
# - Met ~/.local/bin dans le PATH (tma, aif-platform, aif-agents…).
# - Dans un terminal interactif hors tmux, ouvre la session tmux du dossier courant (tma).
#   Après un détachement (d, Save & exit), le shell reprend.
# Pas de tmux : déjà dans tmux, terminal intégré de VS Code / Cursor, shell lancé par Claude Code,
# pas de tty, shell avec une commande (`zsh -lic tma` lance déjà tma), pane Herdr (HERDR_ENV=1),
# ou AIF_DECK=off (interrupteur d'ai-dotdeck ; aif-deck off coupe aussi les touches Windows Terminal).

case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) PATH="$HOME/.local/bin:$PATH"; export PATH ;;
esac

case $- in
  *i*)
    if [ -z "${TMUX:-}" ] && [ "${AIF_DECK:-on}" != off ] && [ -z "${HERDR_ENV:-}" ] && [ -z "${CLAUDECODE:-}" ] \
      && [ "${TERM_PROGRAM:-}" != vscode ] && [ -t 0 ] && [ -t 1 ] \
      && [ -z "${ZSH_EXECUTION_STRING:-}${BASH_EXECUTION_STRING:-}" ] \
      && command -v tmux >/dev/null 2>&1 && [ -x "$HOME/.local/bin/tma" ]; then
      "$HOME/.local/bin/tma"
    fi
    ;;
esac
