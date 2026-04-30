---
name: Infinite scroll commun
overview: Mettre en place un chargement progressif commun pour les listes de poèmes (home + profil) afin de garantir une UX homogène sur mobile et web, tout en conservant les filtres.
todos:
  - id: create-shared-infinite-scroll-hook
    content: Créer un hook partagé de chargement paginé/infinite scroll (IntersectionObserver + état commun)
    status: completed
  - id: migrate-home-to-shared-loader
    content: Migrer Home.tsx vers le hook commun et retirer la pagination locale
    status: completed
  - id: migrate-profile-lists-to-shared-loader
    content: Migrer PoemsGallery.tsx (mes favoris/mes poèmes) vers le même mécanisme de chargement
    status: completed
  - id: unify-loading-ui
    content: Harmoniser le loader visuel (sentinel + spinner) sur toutes les vues de liste
    status: completed
isProject: false
---

# Infinite scroll commun — Listes de poèmes

## Diagnostic du bug
Dans [`src/components/Home.tsx`](src/components/Home.tsx), `loadPoems` est un `useCallback` dont `page` fait partie des dépendances. Quand `page` change, `loadPoems` est recréé, ce qui déclenche le `useEffect([searchTerm, loadPoems])` (ligne 149) qui appelle `setPage(1)` → reset systématique à la page 1.

## Objectif d'homogénéité
Au lieu d'implémenter une solution dédiée à la home, utiliser un mécanisme unique de chargement progressif pour :
- [`src/components/Home.tsx`](src/components/Home.tsx)
- [`src/components/Poems/PoemsGallery.tsx`](src/components/Poems/PoemsGallery.tsx)

## Solution : hook partagé + infinite scroll

### 1) Créer un hook commun de chargement
Ajouter un hook réutilisable (ex: [`src/hooks/useInfinitePoems.ts`](src/hooks/useInfinitePoems.ts)) qui centralise :
- `items` (liste affichée)
- `isInitialLoading` / `isLoadingMore`
- `hasMore`
- `resetAndLoad()` (reset page 1 + rechargement)
- `loadMore()` (append page suivante)
- `sentinelRef` (IntersectionObserver)

Ce hook prend en paramètre une fonction `fetchPage(page, limit)` pour rester compatible avec les différentes sources :
- `getAllPoems/getLatestPoems/getMostAppreciatedPoems` sur la home
- `fetchUserPoems/getSavedPoems` dans le profil

### 2) Migrer `Home.tsx`
Dans [`src/components/Home.tsx`](src/components/Home.tsx) :
- retirer la pagination locale (`page`, `total`, `Pagination`)
- brancher les filtres (`sortMode`, `activeTag`) sur `resetAndLoad()`
- conserver la recherche actuelle (client-side) avec reset explicite de la liste
- afficher le même `sentinel + spinner` en bas de liste

### 3) Migrer `PoemsGallery.tsx`
Dans [`src/components/Poems/PoemsGallery.tsx`](src/components/Poems/PoemsGallery.tsx) :
- supprimer `Pagination` pour `Mes favoris` et `Mes poèmes`
- utiliser le même hook commun
- conserver le switch `created/saved` en déclenchant `resetAndLoad()`
- garder les compteurs (`savedTotal`, `createdTotal`) inchangés

### 4) Uniformiser l'UI de chargement
Réutiliser le même rendu sur toutes les listes :
- même spinner bas de page
- même seuil de déclenchement observer
- même état "fin de liste" (optionnel, discret)

## Impact filtres (tags + filtres généraux)
- Les filtres restent pleinement compatibles.
- À chaque changement de filtre, `resetAndLoad()` remet la liste à la base puis recharge selon le nouveau filtre.
- Le résultat est plus stable qu'avec pagination manuelle (pas de reset involontaire de page).

## Fichiers principaux concernés
- [`src/components/Home.tsx`](src/components/Home.tsx)
- [`src/components/Poems/PoemsGallery.tsx`](src/components/Poems/PoemsGallery.tsx)
- [`src/hooks/useInfinitePoems.ts`](src/hooks/useInfinitePoems.ts)
