---
name: design-system-3-pass-audit
overview: Exécuter un audit/refactor complet en 3 passes (design completeness, leftovers cleanup, centralization) en prenant `graphify-out/graph.json` comme carte canonique, puis appliquer tous les changements de façon atomique et vérifiée.
todos:
  - id: inventory-from-graphify
    content: Établir l’inventaire exhaustif pages/composants/layouts/styles à partir de graphify-out/graph.json et grouper par pass.
    status: completed
  - id: pass1-design-completeness
    content: Appliquer l’audit + corrections design tokens (legacy removal, responsive, dark/light) sur tous les fichiers inventoriés.
    status: completed
  - id: pass2-leftovers-cleanup
    content: Supprimer code/styles/composants morts et tous marqueurs de migration restants après pass 1.
    status: completed
  - id: pass3-centralize-ui
    content: Créer primitives partagées et migrer tous les usages dupliqués (typography/layout/ui/poetry/motion).
    status: completed
  - id: validate-and-report
    content: Exécuter validations, corriger lints introduits, puis générer la sortie finale structurée par pass.
    status: completed
isProject: false
---

# Plan d’audit design-system en 3 passes

## Base de vérité et périmètre
- Carte canonique: [`/home/lgiron/lab/EpidemiedesMotsv2/graphify-out/graph.json`](/home/lgiron/lab/EpidemiedesMotsv2/graphify-out/graph.json) (lecture seule).
- Surface cible complète (sans skip): toutes les pages/composants/layouts/styles recensés dans le graphe, en priorité sous [`/home/lgiron/lab/EpidemiedesMotsv2/src/pages`](/home/lgiron/lab/EpidemiedesMotsv2/src/pages), [`/home/lgiron/lab/EpidemiedesMotsv2/src/components`](/home/lgiron/lab/EpidemiedesMotsv2/src/components), [`/home/lgiron/lab/EpidemiedesMotsv2/src/layouts`](/home/lgiron/lab/EpidemiedesMotsv2/src/layouts), [`/home/lgiron/lab/EpidemiedesMotsv2/src/styles`](/home/lgiron/lab/EpidemiedesMotsv2/src/styles).
- Sources de tokens/règles à harmoniser: [`/home/lgiron/lab/EpidemiedesMotsv2/src/styles/theme.ts`](/home/lgiron/lab/EpidemiedesMotsv2/src/styles/theme.ts), [`/home/lgiron/lab/EpidemiedesMotsv2/src/styles/globals.css`](/home/lgiron/lab/EpidemiedesMotsv2/src/styles/globals.css), [`/home/lgiron/lab/EpidemiedesMotsv2/tailwind.config.js`](/home/lgiron/lab/EpidemiedesMotsv2/tailwind.config.js), [`/home/lgiron/lab/EpidemiedesMotsv2/src/context/ThemeContext.tsx`](/home/lgiron/lab/EpidemiedesMotsv2/src/context/ThemeContext.tsx).

## Pass 1 — Design completeness audit + fix
- Balayer chaque page/composant référencé par graphify et remplacer les classes/valeurs legacy par les tokens partagés (`theme`, utilitaires, classes Tailwind cohérentes).
- Supprimer les styles inline hérités de l’ancien design quand ils doublonnent les tokens.
- Vérifier la cohérence responsive mobile/tablette/desktop sur les patterns communs (conteneurs, typographie, boutons, cartes, formulaires, nav).
- Vérifier la cohérence dark/light partout où `dark:` est utilisé (et aligner avec `ThemeContext`).

## Pass 2 — Leftovers removal
- Identifier et supprimer les classes CSS/propriétés custom non utilisées après pass 1 (notamment dans `globals.css`, `tailwind.scss`, éventuels modules CSS historiques).
- Identifier les composants morts (non importés/non rendus), puis les supprimer proprement.
- Retirer tous les blocs commentés liés ancien design et résoudre/supprimer les marqueurs `TODO`/`FIXME` relatifs au design.
- Dédupliquer les définitions conflictuelles de tokens/styles en gardant une seule source de vérité.

## Pass 3 — Centralisation/refactor
- Créer/normaliser des primitives partagées pour typographie, wrappers de page/section, et variants UI récurrents (boutons/cartes/tags/links).
- Unifier les patterns poetry répliqués (poem card, author/metadata, verse display) dans des composants canoniques sous un dossier dédié, puis migrer tous les usages.
- Extraire les animations/transitions répétées vers utilitaires/classes partagées.
- Assurer typage strict des props (TypeScript) et responsabilité unique par composant.

## Validation et livrables
- Lancer lint ciblé sur les fichiers touchés puis corriger les régressions introduites.
- Vérifier que routes/pages dynamiques restent intactes (pas de changement de routing ni de contenu poétique).
- Produire en sortie le tableau demandé (Pass / Files Modified / Files Deleted / Components Created) + liste des fichiers modifiés par pass avec note d’une ligne.
- Mettre à jour la documentation de suivi imposée (Local Brain journal d’implémentation + page projet) au même tour, sans toucher au fichier `graphify-out`.
