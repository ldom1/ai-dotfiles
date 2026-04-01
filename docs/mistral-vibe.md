# Mistral Vibe et ce dépôt

[Mistral Vibe](https://docs.mistral.ai/mistral-vibe/introduction/quickstart) peut charger les mêmes skills Agent que Claude Code (`SKILL.md` + dossier par skill).

## Découverte des skills

Vibe assemble les répertoires de recherche (voir [Agents & Skills](https://docs.mistral.ai/mistral-vibe/agents-skills)) :

- global : `~/.vibe/skills/`
- projet : tout dossier `.vibe/skills/` trouvé sous le répertoire de travail (parcours borné)
- optionnel : `skill_paths` dans le `config.toml` **effectivement chargé**

Chaque sous-dossier direct contenant un fichier `SKILL.md` devient un skill nommé d’après le dossier (et le frontmatter `name` doit coïncider).

## `available_skills` et outil `skill`

Une fois découverts, les skills apparaissent côté agent dans la liste **`available_skills`** (résumé dans le prompt système).

L’outil intégré **`skill`** prend un argument `name` : il charge le skill depuis le gestionnaire, lit le `SKILL.md`, et **injecte le contenu** dans le fil de conversation pour appliquer instructions et workflows spécialisés quand la tâche correspond à ce skill.

## Configuration dans `ai-dotfiles`

Ce repo expose `brain-sync` et `brain-load` via **`.vibe/skills/`** : liens symboliques vers `skills/brain-sync` et `skills/brain-load`, sans dupliquer les fichiers.

Prérequis typiques :

1. Dossier de travail = racine du clone (ou équivalent).
2. Dossier **trusted** dans Vibe (voir [Configuration](https://docs.mistral.ai/mistral-vibe/introduction/configuration), trusted folders).

## Piège : `config.toml` projet

Si tu crées **`.vibe/config.toml`** à la racine du projet, Vibe peut l’utiliser **en lieu et place** de `~/.vibe/config.toml` quand le projet est trusted, ce qui fait disparaître providers / modèles globaux. Pour n’étendre que les skills, utilise `.vibe/skills/` (comme ici) ou ajoute des chemins absolus dans **`skill_paths`** dans ton **`~/.vibe/config.toml`**.
