# Checklist manuelle — vue sessions / agents tmux

À cocher par Louis sur chaque plateforme : **WSL** (Ubuntu 22.04, tmux 3.2a, Windows Terminal) et **26.04** (tmux 3.6a, Ghostty). Les tests automatiques sont dans `tests/` (`npx --yes bats@1.13.0 tests/`, `tests/container.sh`, `cd sidebar && cargo test`).

Préparation : `bash ~/ai-dotfiles/scripts/install.sh`, puis `prefix r` dans tmux.

## Étapes 1 et 2 — plateforme, touches, état

| Vérification | WSL | 26.04 |
|---|---|---|
| Ctrl+Shift+O / E : split à droite / en bas (pas de split Ghostty) | [ ] | [ ] |
| Ctrl+Shift+N : nouvelle session ; Ctrl+Shift+B : sidebar affichée / masquée | [ ] | [ ] |
| Ctrl+Shift+X : ferme le pane (confirmation si `claude` y tourne) | [ ] | [ ] |
| Ctrl+Shift+K et `prefix X` : tuent la session après confirmation | [ ] | [ ] |
| `prefix O/E/N/B/Q/Tab//` : mêmes actions, sauvegarde et sortie, dernière session, aide tmux | [ ] | [ ] |
| Sélection à la souris : « Copied to clipboard », collage avec accents | [ ] | [ ] |
| `printf 'héllo àccents' \| aif-platform copy` puis coller : accents intacts | [ ] | [ ] |
| `claude` dans un pane, puis `aif-agents list --json` : état `done` → `running` → `check` sur une permission | [ ] | [ ] |
| Agent en `check` dans une session en arrière-plan : notification système (WSL : BurntToast installé) | [ ] | [ ] |

## Étape 3 — onglet AGENTS et aperçu

Ouvrir la sidebar : `tmux split-window -hbf -l 50 aif-sidebar`.

| Vérification | WSL | 26.04 |
|---|---|---|
| Version d'ai-dotfiles en haut à droite | [ ] | [ ] |
| Un agent qui demande une permission apparaît dans TO CHECK avec `[1 Yes] [2 Always] [3 No]` | [ ] | [ ] |
| `1` dans la sidebar : Claude Code exécute l'outil (permission accordée une fois) | [ ] | [ ] |
| `2` : permission accordée et retenue ; `3` : refus | [ ] | [ ] |
| Question `AskUserQuestion` : la question et ses options apparaissent ; `1`/`2` choisit l'option dans Claude Code | [ ] | [ ] |
| `i`, texte, Entrée : la réponse libre arrive dans Claude Code (question : « Type something » ; permission : refus avec raison) | [ ] | [ ] |
| Après une réponse : l'agent passe en RUNNING avec « you answered: … » | [ ] | [ ] |
| `⏎` : tmux va sur la session, la fenêtre et le pane de l'agent | [ ] | [ ] |
| `p` : aperçu à droite (≈ 40 %), le pane courant reste visible ; `Tab` Output / Diff ; `⏎` va à l'agent ; `Esc` ferme | [ ] | [ ] |
| `/` filtre ; `o` change le tri ; `1`–`9` saute à l'agent de ce numéro | [ ] | [ ] |
| Clic sur un onglet, une carte, un bouton de réponse | [ ] | [ ] |
| 10 agents : la sidebar reste fluide (spinner régulier, touches sans retard) | [ ] | [ ] |
