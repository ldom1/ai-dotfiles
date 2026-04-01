# Mistral Vibe — ce dépôt

## Skills et outil `skill`

Vibe découvre les skills sur disque (dont ce dossier `.vibe/skills/`), construit la liste **`available_skills`**, et expose l’outil **`skill`**.

Comportement (aligné sur l’implémentation Vibe) :

- Les chemins parcourus incluent notamment `~/.vibe/skills/`, les dossiers projet `.vibe/skills/`, et les entrées **`skill_paths`** du `config.toml` actif.
- Le **prompt système** mentionne les skills disponibles (noms + descriptions courtes).
- Quand une tâche correspond à un skill listé, l’agent appelle l’outil **`skill`** avec le **nom** du skill : le contenu complet du `SKILL.md` (instructions, workflows, ressources) est alors **injecté dans le contexte** de la conversation.

Ici, `brain-sync` et `brain-load` sont exposés via des liens symboliques vers `../../skills/<id>/` pour ne pas dupliquer les sources.

## Confiance dossier

Le dépôt doit être **trusted** dans Vibe, et tu dois lancer Vibe avec ce dossier comme répertoire de travail (souvent `cd` dans le clone puis `vibe`), pour que `.vibe/skills/` soit pris en compte dans la découverte projet.

## Ne pas écraser ta config globale

Si tu ajoutes un **`.vibe/config.toml` à la racine du projet**, Vibe peut le charger **à la place** de `~/.vibe/config.toml` lorsque le dossier est trusted — ce qui supprimerait modèles / providers globaux. Pour n’ajouter que des skills, préfère ce répertoire `.vibe/skills/` (ou des `skill_paths` absolus dans **`~/.vibe/config.toml`**).
