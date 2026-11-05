# ADR 0001 — Sidebar sessions / agents tmux

- Statut : **accepté** le 2026-11-05 : option B, sous-option B1 (Rust + ratatui), look and feel inspiré de claude-squad
- Date : 2026-11-05
- Contexte : branche `feat/tmux-agents`, spécification « vue sessions / agents tmux » (étapes 3 à 5)

## Contexte

La maquette demande, dans une sidebar tmux : trois onglets (SESSIONS, AGENTS, ACTIONS), un champ de filtre, des boutons de réponse qui envoient des touches au pane de l'agent, et un aperçu à droite (≈ 40 % de la fenêtre) avec capture du pane et diff git. Les données viennent de `aif-agents list --json` (état écrit par les hooks Claude Code, étape 2).

Faits relevés dans opensessions `v0.2.0-alpha.12` (`~/.tmux/plugins/opensessions`) :

- 17,9 k lignes de Rust, 4 crates. Le sidebar reçoit des instantanés JSON du serveur par WebSocket (`protocol.rs:18-56`).
- Mise en page fixe et verticale (`renderer.rs:117-157`, fichier de 3 498 lignes). Pas d'onglets ; saisie de texte seulement dans la modale de thème (`app.rs:73-77`) ; lettres prises comme raccourcis globaux (`app.rs:513-556`) ; Tab change de session (`app.rs:558`).
- Aucun `send-keys` ni `capture-pane` (trait `MuxProvider`, `mux.rs:52-150`). Largeur bornée à 20–80 colonnes et réimposée par le serveur (`sidebar_width_sync.rs`, `lib.rs:1347`).
- État des agents deviné par lecture des transcripts toutes les 2 s : « waiting » = dernier tool_use et 3 s sans écriture (`agent_watchers.rs:10,96-98`). Les hooks Claude Code ne sont pas lus.
- Règles amont : « Do not substitute … layout behavior, protocol shape … unless the migration docs are updated by a human reviewer first » (`apps/tui-rs/AGENT.md:5`) ; anti-référence produit : « Heavy dashboard chrome inside a narrow terminal pane » (`PRODUCT.md:27`).
- Activité : dernier commit et dernière release le 2026-06-07 ; depuis mai, 46 commits sur 49 viennent d'un seul auteur ; pas de CONTRIBUTING.
- Notre unique patch (179 lignes, `renderer.rs`) a déjà dû être régénéré deux fois. Il n'existe que si `install.sh` compile ; sur Ubuntu 26.04 le binaire fourni passe `ldd`, donc pas de patch (constat 0.3).

## Options

| | Effort v1 (estimation) | Risque de maintenance | Règle des 12 mois | Ce qui marche en v1 |
|---|---|---|---|---|
| **A. Patches opensessions** | Élevé : 4 fonctions absentes, dont l'aperçu qui contredit la borne de largeur et les invariants du serveur. Plusieurs patches sur `renderer.rs`, `app.rs`, `input.rs`, `lib.rs`, `mux.rs`. | Élevé : rebase de chaque patch à chaque release ; compilation obligatoire sur les deux machines ; états toujours devinés sauf patch du serveur en plus. | OK jusqu'au 2027-06-07, puis exception à documenter si l'amont reste muet. | Arbre des sessions, branche git, lazydiff, thèmes. Pas d'onglets, d'aperçu ni de réponses tant que les patches ne sont pas écrits. |
| **B. Sidebar maison** lisant `aif-agents list --json` | Moyen : la donnée est prête (étape 2) ; reste l'interface. | Moyen : code à nous, mais aucune dépendance à un amont figé. | OK : dépendances actives (voir sous-options). | Toute la maquette, avec des états exacts (hooks). Perd : branche git par session (à refaire, 1 appel git), lazydiff, autres agents (hors périmètre). |
| **C. Contribuer en amont, A en attendant** | A + revue amont incertaine. | Celui de A, sans date de fin. | Comme A. | Comme A. L'amont est inactif depuis 5 mois et son produit refuse le « dashboard chrome » dans un pane étroit. |
| **D. Adopter un gestionnaire existant** (claude-squad 8,7 k ★, release 2026-08-20 ; agent-deck 1,2 k ★, 2026-11-02 ; ccmanager 1,3 k ★, 2026-10-27) | Faible pour l'outil, mais il remplace `tma`, la sidebar et le flux tmux actuels. | Faible côté code. | OK. | Leur interface, pas la maquette : applications plein écran qui créent elles-mêmes les sessions. claude-squad : worktree obligatoire, état lu dans le contenu du pane, pas de réponse sans s'attacher. agent-deck (le plus proche) : hooks Claude et réponse sans s'attacher, mais seulement pour ses propres sessions `agentdeck_*` ; un `claude` lancé à la main dans un split n'a pas d'état ; pas de diff. ccmanager : sans tmux. Aucun ne gère tmux-resurrect ni n'est une sidebar à côté des panes. |

Sous-options de B :

- **B1. Rust + ratatui** (23 k ★, release 2026-06-19) : même chaîne que la compilation d'opensessions aujourd'hui. Demande `cargo` sur les deux machines (c'est déjà le point faible de A sur 26.04).
- **B2. Python + Textual** (37,6 k ★, release 2026-06-30) : onglets (`TabbedContent`), champ (`Input`), boutons, souris et mise en page en colonnes fournis ; lancé par `uv run` (script PEP 723), sans compilation. Démarrage ≈ 0,5 s, une fois (la sidebar reste ouverte).

## Décision

B1 : sidebar maison en Rust (crate `sidebar/`, binaire `aif-sidebar`), qui lit seulement `aif-agents` et tmux. Louis a choisi ratatui plutôt que Textual. Look and feel inspiré de claude-squad (cartes sur plusieurs lignes, fond de sélection, onglets soulignés en accent, menu de touches en pied), avec la palette de la spécification et la version d'ai-dotfiles en haut à droite.

Briques : ratatui 0.30 (interface), crossterm 0.29 par la réexportation de ratatui (terminal, événements ; release 2025-04-05, plus de 12 mois : exception, c'est le backend par défaut de ratatui), serde / serde_json (JSON), textwrap (retour à la ligne, largeur Unicode), anyhow (erreurs). Rejetés : tui-input (champ de saisie, peu utilisé ; un `String` suffit pour une ligne), ansi-to-tui (capture colorée ; l'aperçu v1 affiche le texte brut).

## Recommandation initiale

**B**, ce qui confirme la proposition de la spécification : les quatre fonctions manquent dans opensessions, l'aperçu va contre ses invariants, et l'amont interdit ce type de changement sans revue. D est écarté parce que ces outils remplacent le flux tmux au lieu de l'équiper.

Pour la techno, je recommande **B2 (Textual)** plutôt que B1. Elle supprime la compilation sur chaque machine (cause du constat 0.3), et ses widgets couvrent la maquette, ce qui donne moins de code à maintenir. B1 reste valable si tu veux un binaire unique sans Python.

Conséquences de B : opensessions est retiré (`config/tmux.conf`, `install.sh`, patch) quand la nouvelle sidebar couvre les sessions ; le constat 0.3 disparaît avec lui.
