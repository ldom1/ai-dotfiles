---
name: wiki sync recovery
overview: Determine why wiki content did not update and switch to a direct, reliable local-wiki source workflow with optional CI trigger.
todos:
  - id: choose-source
    content: Choose `.wiki/` as canonical wiki source and deprecate `docs/wiki/`
    status: completed
  - id: align-script
    content: Refactor update-wiki.sh to publish from `.wiki/` directly
    status: completed
  - id: simplify-ci
    content: Reduce CI wiki sync to manual dispatch or remove it
    status: completed
  - id: update-docs
    content: Update README/CONTRIBUTING/CHANGELOG to reflect the new process
    status: completed
  - id: verify-live
    content: Push and verify wiki pages render with Skills structure
    status: completed
isProject: false
---

# Fix Wiki Update Flow

## What happened

- The current sync script publishes from `docs/wiki/` into the separate wiki repo (`.wiki.git`), but your latest visible wiki home still reflects old pages: [Home · ldom1/ai-dotfiles Wiki](https://github.com/ldom1/ai-dotfiles/wiki).
- With your new local clone at `.wiki/`, maintaining both `.wiki/` and `docs/wiki/` creates duplication and drift.

## Recommended direction (lean and reliable)

- Make `.wiki/` the single source of truth for wiki content.
- Keep one explicit manual command to publish when needed (`scripts/update-wiki.sh`), and keep CI wiki publishing optional/minimal.
- Keep CI checks for code quality, but avoid hidden auto-publish surprises.

## Concrete changes to make

- Update [`scripts/update-wiki.sh`](/home/lgiron/ai-dotfiles/scripts/update-wiki.sh):
  - publish from `.wiki/` directly (no temp clone-copy from `docs/wiki/`)
  - run `git -C .wiki add -A && git -C .wiki commit && git -C .wiki push`
  - keep PAT fallback (`WIKI_PUSH_TOKEN`) for CI-only path if needed.
- Remove `docs/wiki/` usage from docs and process notes:
  - [`README.md`](/home/lgiron/ai-dotfiles/README.md)
  - [`docs/wiki/README.md`](/home/lgiron/ai-dotfiles/docs/wiki/README.md) (either delete or replace with deprecation note)
  - [`CHANGELOG.md`](/home/lgiron/ai-dotfiles/CHANGELOG.md)
  - [`CONTRIBUTING.md`](/home/lgiron/ai-dotfiles/CONTRIBUTING.md)
- Simplify CI in [`ci.yml`](/home/lgiron/ai-dotfiles/.github/workflows/ci.yml):
  - either remove wiki-sync job entirely,
  - or keep it only as `workflow_dispatch` manual action that runs after checks.

## Suggested operating model

- Daily/normal: edit wiki pages in `.wiki/` and push intentionally when ready.
- Optional automation: manual workflow dispatch in GitHub Actions if you want server-side publish.

## Verification

- Confirm `.wiki/` branch is clean and ahead/updated after publish.
- Open [wiki Home](https://github.com/ldom1/ai-dotfiles/wiki) and one `Skills/*` page to verify new structure appears.