# Local Brain — Centre névralgique

**Local Brain est la source de vérité unique pour toutes les sessions Claude.**

## Paths

- Vault (WSL) : `/mnt/c/Users/louis/Documents/Local Brain/`
- Vault (Windows) : `C:\Users\louis\Documents\Local Brain`
- Mémoire Claude : `/home/lgiron/.claude/projects/-home-lgiron/memory/` (symlink → vault `docs/memory/`)

## Démarrage de session obligatoire

Au début de chaque session, lire dans l'ordre :
1. `/mnt/c/Users/louis/Documents/Local Brain/IDENTITY.md` — qui est l'utilisateur
2. `/mnt/c/Users/louis/Documents/Local Brain/breadcrumbs.md` — contexte rapide L2
3. `/mnt/c/Users/louis/Documents/Local Brain/docs/memory/MEMORY.md` — mémoire persistante

Si un projet spécifique est mentionné, lire aussi sa fiche dans `projects/`.

## Règles de stockage

Toute information découverte durant une session **doit** être stockée dans Local Brain :

| Type d'information | Où stocker |
|---|---|
| Décision technique, architecture | `resources/knowledge/architecture/` |
| Spec / design doc | `resources/knowledge/architecture/specs/YYYY-MM-DD-nom.md` |
| Plan d'implémentation (superpowers) | `resources/knowledge/architecture/plans/YYYY-MM-DD-nom.md` |
| ADR (Architecture Decision Record) | `resources/knowledge/architecture/adr/` |
| Pattern réutilisable | `resources/knowledge/patterns/` |
| Doc outil / setup | `resources/knowledge/operational/` |
| SOP, procédure | `resources/knowledge/sops/` |
| Projet actif | `projects/<nom>.md` |
| Idée / opportunité | `caps/entrepreneur.md` ou `todo/` |
| Note de session | `daily/YYYY-MM-DD.md` |
| Mémoire persistante Claude | `docs/memory/MEMORY.md` |
| Contexte de session | `docs/context/session-YYYY-MM-DD.md` |

## Superpowers — Plans & Specs dans Local Brain

Quand les skills superpowers créent des artefacts (plans, specs, ADRs), ils vont dans Local Brain :

- **`superpowers:writing-plans`** → créer le plan dans `resources/knowledge/architecture/plans/YYYY-MM-DD-<nom>.md`
- **`superpowers:brainstorming`** → si un design/spec émerge, le sauvegarder dans `resources/knowledge/architecture/specs/`
- **Après implémentation** → mettre à jour le statut du plan et la fiche projet dans `projects/`
- **Ne jamais** créer des plans/specs dans `~/docs/superpowers/` ou dans des dossiers `docs/` de projet — tout va dans Local Brain

**Chemin vault pour superpowers :**
```
/mnt/c/Users/louis/Documents/Local Brain/resources/knowledge/architecture/
├── plans/          ← plans d'implémentation
├── specs/          ← design docs, specs techniques
└── adr/            ← Architecture Decision Records
```

## Règles de mise à jour

- **breadcrumbs.md** : mettre à jour si un nouveau projet démarre, une ressource clé est créée
- **MEMORY.md** : mettre à jour avec les faits importants persistants entre sessions
- **Liens** : toujours créer des `[[wiki-links]]` entre les notes liées
- **Frontmatter** : chaque note a `title`, `created`, `tags`, `status`

## Structure PARA

```
Local Brain/
├── IDENTITY.md             ← L1 : profil utilisateur
├── breadcrumbs.md          ← L2 : index rapide
├── daily/                  ← capture quotidienne
├── projects/               ← actions court terme
├── caps/                   ← responsabilités long terme
│   ├── developer.md
│   ├── student.md
│   └── entrepreneur.md
├── resources/knowledge/    ← L3 : docs profondes
│   ├── architecture/
│   ├── patterns/
│   ├── operational/        ← lab, claude, mcps, rtk...
│   └── sops/
├── docs/                   ← fichiers Claude
│   ├── memory/MEMORY.md    ← L1 mémoire
│   └── context/            ← contexte session
├── todo/
└── archive/
```
