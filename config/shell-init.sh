# shellcheck shell=sh
# ai-dotfiles : initialisation du terminal. ~/.zshenv, ~/.zshrc et ~/.bashrc la sourcent (ligne
# ajoutée par scripts/install.sh). Met ~/.local/bin dans le PATH (ai-dotfiles, local-ci,
# aif-agent-hook, outils installés par uv et npm). ~/.zshenv couvre les shells de connexion non
# interactifs qu'Orca lance pour ses agents.

case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) PATH="$HOME/.local/bin:$PATH"; export PATH ;;
esac
