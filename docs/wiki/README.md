# GitHub wiki source (Skills namespace)

GitHub wikis are a **separate git repo** (`https://github.com/ldom1/ai-dotfiles.wiki.git`). This folder is the source of truth for the **`Skills/`** pages.

## Automated publish (default)

On **push to `main`**, after **CI** jobs (shellcheck, JSON, skill layout) succeed, the **Publish wiki** job runs **only if** the push touched `docs/wiki/**`, `scripts/update-wiki.sh`, or `.pre-commit-config.yaml` (see `.github/workflows/ci.yml` + `dorny/paths-filter`). It runs **`pre-commit run update-wiki --hook-stage manual`**, which executes [`scripts/update-wiki.sh`](../scripts/update-wiki.sh).

- The job uses `WIKI_PUSH_TOKEN` if set (repo secret); otherwise `GITHUB_TOKEN`. **`GITHUB_TOKEN` usually cannot push the `.wiki.git` repo** — if the wiki never updates, add a **classic PAT** (`repo` scope) as secret **`WIKI_PUSH_TOKEN`**. In the repo: **Settings → Secrets and variables → Actions**.
- **Publish wiki did not run:** the path filter only runs the job when `docs/wiki/**`, `scripts/update-wiki.sh`, `.pre-commit-config.yaml`, or `.github/workflows/ci.yml` change. If you merged CI before `docs/wiki` was on `main` in the same push, the job may have been skipped — run **Actions → CI → Run workflow** (workflow dispatch) on `main` after checks pass, or push any edit under `docs/wiki/`.
- Forks skip the sync (script exits 0).

## Manual publish

```bash
# from the ai-dotfiles repo root:
export WIKI_PUSH_TOKEN=ghp_...   # or rely on ssh + URL edit inside script for local only — see update-wiki.sh
bash scripts/update-wiki.sh
```

Or copy files by hand:

```bash
git clone https://github.com/ldom1/ai-dotfiles.wiki.git /tmp/ai-dotfiles-wiki
cp docs/wiki/Skills.md /tmp/ai-dotfiles-wiki/Skills.md
mkdir -p /tmp/ai-dotfiles-wiki/Skills
cp docs/wiki/Skills/*.md /tmp/ai-dotfiles-wiki/Skills/
cd /tmp/ai-dotfiles-wiki && git add -A && git commit -m "docs(wiki): skill pages under Skills/" && git push
```

## After migration

- README links use `https://github.com/ldom1/ai-dotfiles/wiki/Skills/<Name>`.
- Optional: replace legacy top-level pages (`Brain-Sync`, etc.) with short notes that link to `Skills/Brain-Sync` so old URLs keep working.

## Canonical instructions

Full agent instructions always live in the repo: `skills/<name>/SKILL.md`. Wiki pages here are **human-facing overviews** plus deep links.
