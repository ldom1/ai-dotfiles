---
name: veille
description: Use when external sources (articles, repos, skills, tools) from AI / agent tech watch must be compared with a target project — "veille", "regarde ce repo", "ça vaut le coup d'intégrer ?", "gap analysis".
---

# veille

**REQUIRED BACKGROUND:** the router `~/ai-dotfiles/skills/veille-technique/SKILL.md` holds the shared steps (cadrage, baseline, rapport, trace, plan). Read it first if it is not in context. This file replaces its step 2 only.

Verdicts: **Adopter** (as is) · **Adapter** (take the idea, not the code) · **Surveiller** (re-check at a date) · **Ignorer** (reason).

## Baseline source

If an `audit` artifact for the target exists in the ledger (`grep -n 'Audit' "$BP/resources/knowledge/veille-technique.md"`), read it with the Artifact tool (`action: read`) and use its per-component blocks as the baseline. Otherwise use the router's step 1.

## Analyse each source

One source: fetch it in the main context. `WebFetch` the page; for a GitHub repo read the README, the file tree (`https://api.github.com/repos/<owner>/<repo>/contents/<path>`) and each `SKILL.md` via `raw.githubusercontent.com`.

Two or more sources: dispatch one `general-purpose` subagent per source in parallel (Sonnet via `CLAUDE_CODE_SUBAGENT_MODEL`: fetch-and-summarise work, no design). Each prompt:

- is read-only: `WebFetch` only, no file writes, no clone, no install;
- contains the baseline summary (≤ 250 words) and says "do not re-describe the baseline; state only what the source adds, duplicates or contradicts";
- asks for the router's component block, one per separable mechanism (a repo of 50 skills gives grouped blocks, not one), ≤ 300 words each, every claim ending with a source URL or `(inférence)`;
- ends with `**Affirmation vérifiée :**` one claim checked against a second source or the raw file, plus licence and last commit date.

A source split into components by the subagent gets one verdict per component, not per source.

## Verify before synthesis

For each source, fetch the raw file yourself and quote the exact wording of the one claim the verdict rests on (a threshold, a default, a percentage and its measurement conditions). A subagent's paraphrase is not a quote.

Raw text, by host:
- GitHub: `gh api repos/<owner>/<repo>/contents/<path> --jq .content | base64 -d`.
- Other pages: `npx -y firecrawl-cli@1.26.10 scrape "<url>" --only-main-content` prints Markdown to stdout. It needs no key and is rate-limited per IP. The page goes to Firecrawl's cloud: never use it for private or employer URLs.
- If both fail, quote from `WebFetch` and label the quote `paraphrase`.

## Common mistakes

- Treating a mirror or fork as the upstream: check `MIRROR.md`, `plugin.json` author and the commit log.
- Grouping a bundle as one component: a router plus 24 principle skills is several verdicts.
- Taking "N% savings" at face value: record the corpus, the scenario count, the token estimator and what was excluded (worker tokens, latency, quality loss).
