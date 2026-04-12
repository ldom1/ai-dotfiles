---
name: Améliorer CLAUDE.md
overview: Rendre explicites les garanties d’exécution (pas d’auto-run produit pour brain-sync/load), lever l’ambiguïté sur `$BRAIN_PATH`, fiabiliser le chemin RTK, et compléter la liste des skills — le tout en restant court et actionnable.
todos:
  - id: session-wording
    content: "Réécrire Session Start/End : obligation agent, pas d’auto-run produit ; lien /brain-sync + bash"
    status: completed
  - id: brain-path-clarity
    content: "Section Memory : BRAIN_PATH = config/brain.env ; pas d’injection load.sh ; filet grep/read"
    status: completed
  - id: rtk-path-hooks
    content: RTK chemin absolu + distinction PreToolUse Bash vs brain-sync
    status: completed
  - id: skills-list
    content: Lister brain-sync, brain-load, create-pr ; phrase scope ai-dotfiles
    status: completed
isProject: false
---

# Plan : clarifier CLAUDE.md (Brain, hooks, skills)

## Constat (repo)

- **brain-sync / brain-load** : aucun hook « session » dans `[/.claude/settings.json.tpl](.claude/settings.json.tpl)` ; seul **PreToolUse / Bash** appelle `[/.claude/hooks/rtk-rewrite.sh](.claude/hooks/rtk-rewrite.sh)`. Les docs le confirment : p.ex. `[docs/brain-sync.md](docs/brain-sync.md)` (Cursor = règles agent ; Claude Code = `CLAUDE.md` + habitudes ou chargement de skill), `[docs/mistral-vibe.md](docs/mistral-vibe.md)` (slash command = charge du texte, **pas** d’exécution shell).
- `**$BRAIN_PATH`** : `[skills/brain-load/_brain_env.sh](skills/brain-load/_brain_env.sh)` et `[load.sh](skills/brain-load/load.sh)` **sourcent** `brain.env` uniquement dans le processus bash du script ; la sortie utile pour Claude est le **contenu de la note** (stdout), pas une exportation d’environnement vers Claude Code.
- `**RTK.md`** : présent à `[/.claude/RTK.md](.claude/RTK.md)` — le lien relatif fonctionne si le contexte part du dossier `.claude/`, mais `**~/ai-dotfiles/.claude/RTK.md**` est plus robuste dans un merge multi-fichiers.
- **Skills dans ce dépôt** : trois dossiers avec `SKILL.md` — `[brain-sync](skills/brain-sync/SKILL.md)`, `[brain-load](skills/brain-load/SKILL.md)`, `[create-pr](skills/create-pr/SKILL.md)`. Ne lister que `/create-pr` laisse croire à un inventaire incomplet alors que c’est l’ensemble « dotfiles ».

## Modifications proposées dans `[.claude/CLAUDE.md](.claude/CLAUDE.md)`

### 1. Section Session (Start / End)

- Remplacer l’ambiguïté « instruction que le produit exécute » par une formulation du type :
  - **Obligation agent** : au **premier tour** de session (sauf si l’utilisateur dit explicitement de ne pas le faire), exécuter en bash les deux commandes **Start** ; au **dernier tour** résolu (ou quand l’utilisateur termine), exécuter **End**.
  - **Pas d’automatisation Claude Code** : préciser en une ligne que ces scripts ne sont **pas** déclenchés par un hook session (contrairement au hook RTK sur Bash, voir section dédiée).
- Option courte : renvoyer vers `**/brain-sync`** et `**/brain-load**` comme rappels « charge le SKILL » *sans* exécuter git — le bash reste la source de vérité (aligné avec `[skills/brain-sync/SKILL.md](skills/brain-sync/SKILL.md)`).

### 2. Section Memory (`$BRAIN_PATH`)

- Expliquer en une phrase : `**$BRAIN_PATH` dans ce fichier désigne la variable définie dans `~/ai-dotfiles/config/brain.env*`* (ou `BRAIN_ENV_FILE`) ; ce n’est **pas** injecté dans l’environnement du modèle par `load.sh`.
- Donner un filet de secours minimal pour l’agent : **lire** `config/brain.env` (ou faire un `grep '^BRAIN_PATH=' ~/ai-dotfiles/config/brain.env`) quand un chemin absolu du vault est nécessaire avant d’avoir exécuté quoi que ce soit.
- Garder `[LocalBrain.md](.claude/LocalBrain.md)` comme index ; si tu préfères éviter toute dépendance au contenu du vault dans le dépôt, tu peux aussi noter « idem vault : remplacer mentalement par la valeur du `.env` ».

### 3. Bash hooks + RTK

- Remplacer `RTK.md` par `**~/ai-dotfiles/.claude/RTK.md`** (ou chemin relatif **depuis la racine du repo** si tu standardises sur une seule convention — l’absolu `~/ai-dotfiles/...` est le plus clair pour Claude Code).
- Une ligne : le hook configuré est **PreToolUse → Bash** (voir `settings.json.tpl`), pas brain-sync.

### 4. Skills

- Étendre la liste en **3 puces** alignées sur les skills réels :
  - `**/brain-sync`** — rappel procédure + chemins ; **git = `sync.sh`**.
  - `**/brain-load**` — note projet + flux CAP / instantiate ; **contenu = `load.sh`**.
  - `**/create-pr**` — PR GitHub (voir `[disable-model-invocation](skills/create-pr/SKILL.md)` : surtout sur invocation utilisateur).
- Une phrase de bas de section : plugins / superpowers etc. peuvent ajouter d’autres slash commands ; cette liste couvre **ai-dotfiles** uniquement.

### 5. Ce qu’on ne change pas (volontairement)

- Sections **Compaction**, **FinOps**, **Long runs** : déjà alignées avec tes objectifs ; pas d’allongement inutile.
- Pas de nouveau fichier markdown « doc » sauf si tu le demandes explicitement (règle utilisateur : éviter les fichiers non demandés).

## Vérification après coup

- Relire le fichier : **< ~40 lignées**, pas de contradictions avec `[README.md](README.md)` / `[docs/brain-sync.md](docs/brain-sync.md)`.
- (Optionnel) Si tu utilises une machine où `~/ai-dotfiles` n’est pas le chemin du repo, remplacer le préfixe absolu par une variable utilisateur ou « chemin de ce dépôt clone » — à trancher selon ta politique (une phrase suffit).

