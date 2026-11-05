# Checklist manuelle — vue sessions / agents tmux

À cocher par Louis sur chaque plateforme : **WSL** (Ubuntu 22.04, tmux 3.2a, Windows Terminal) et **26.04** (tmux 3.6a, Ghostty). Les tests automatiques sont dans `tests/` (`npx --yes bats@1.13.0 tests/`, `tests/container.sh`, `cd sidebar && cargo test`).

Préparation : `bash ~/ai-dotfiles/scripts/install.sh`, puis `prefix r` dans tmux.

## Étapes 1 et 2 — plateforme, touches, état

| Vérification | WSL | 26.04 |
|---|---|---|
| Ctrl+Shift+O / E : split à droite / en bas (pas de split Ghostty) | [ ] | [ ] |
| Ctrl+Shift+N : nouvelle session ; Ctrl+Shift+B : sidebar affichée / masquée | [ ] | [ ] |
| Ctrl+Shift+X : ferme le pane (confirmation si `claude` y tourne) | [ ] | [ ] |
| Ctrl+Shift+K et `prefix X` : écran Kill session dans la sidebar | [ ] | [ ] |
| `prefix O/E/N/B/Q/Tab//` : mêmes actions, sauvegarde et sortie, dernière session, aide tmux | [ ] | [ ] |
| Sélection à la souris : « Copied to clipboard », collage avec accents | [ ] | [ ] |
| `printf 'héllo àccents' \| aif-platform copy` puis coller : accents intacts | [ ] | [ ] |
| `claude` dans un pane, puis `aif-agents list --json` : état `done` → `running` → `check` sur une permission | [ ] | [ ] |
| Agent en `check` dans une session en arrière-plan : notification système (WSL : BurntToast installé) | [ ] | [ ] |

## Étape 3 — onglet AGENTS et aperçu

La sidebar s'ouvre seule à gauche de chaque fenêtre (après `install.sh` puis un redémarrage de tmux).

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

## Étape 4 — une seule sidebar, SESSIONS, ACTIONS, écrans

Avant : sauvegarder (`prefix Ctrl-s`), quitter tmux (`tmux kill-server`) et le relancer, pour retirer les hooks d'opensessions du serveur. Puis, dans tmux, `prefix Alt+u` (TPM) supprime le dossier `~/.tmux/plugins/opensessions`.

| Vérification | WSL | 26.04 |
|---|---|---|
| Une seule sidebar à gauche, dans chaque fenêtre et chaque session (y compris après Ctrl+Shift+N et une nouvelle fenêtre) | [x] | [ ] |
| Ctrl+Shift+B : la sidebar disparaît partout, puis revient ; Alt+s lui donne le focus | [x] | [ ] |
| SESSIONS : arbre session → agents → sous-agents ; `▸` sur la session courante ; `⏎` change de session ; `r` renomme | [x] | [ ] |
| Ctrl+Shift+N : écran New session ; étiquettes `new` / `attach` / `name taken → …-2` ; Create & attach crée et bascule | [x] | [ ] |
| Ctrl+Shift+K : écran Kill session (agents listés), pane de travail atténué ; Save & kill sauvegarde puis tue | [x] | [ ] |
| `prefix Q` : écran Save & exit ; `d` détache sans rien arrêter ; Save & exit quitte tmux ; au redémarrage, la disposition revient | [x] | [ ] |
| ACTIONS : cible = session sous le curseur de SESSIONS ; split, zoom sur le pane de travail ; « last save … ago » après `s` | [x] | [ ] |
| Clic droit dans la sidebar : menu rename / new / kill / hide | [x] | [ ] |
| Sans `aif-sidebar` installé : Ctrl+Shift+K et `prefix Q` posent une question y/n | [x] | [ ] |
