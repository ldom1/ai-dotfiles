---
name: search-console
description: Use when the user asks about a site's Google Search Console data — search queries, clicks, impressions, CTR, average position, top pages, traffic drops, indexing or "why is this page not indexed", canonical, sitemaps — or says GSC, Search Console, SEO performance of their own site.
---

# Search Console

Read-only access to Google Search Console through `scripts/gsc.py` (Python stdlib, no install).
It uses the user's own OAuth client and the `webmasters.readonly` scope.

## Setup (once per machine)

Check first: `python3 scripts/gsc.py sites`. Exit code 3 means setup or re-auth is needed.

1. Google Cloud Console: create a project and enable the **Search Console API**.
2. OAuth consent screen: type **External**, add the user's Google account as a **Test user**.
3. Credentials → OAuth client ID → **Desktop app**. Download the JSON.
4. Save it as `~/.config/gsc/credentials.json`.
5. The user runs `! python3 <skill-dir>/scripts/gsc.py auth` (opens a browser; interactive).
   - "Google hasn't verified this app": Advanced → continue.
   - WSL, "connection refused" after consent: copy the address bar, run `gsc.py auth --url '<URL>'`.

While the consent screen stays in **Testing**, Google revokes the refresh token after 7 days.
The script then exits 3 with `invalid_grant`: ask the user to run `auth` again.

## Commands

| Command | Output |
|---|---|
| `gsc.py sites` | properties + permission (TSV) |
| `gsc.py query SITE [--dimensions query,page] [--start D --end D] [--filter page:contains:/blog] [--limit N] [--type web]` | TSV rows: dimensions, clicks, impressions, ctr, position |
| `gsc.py inspect SITE URL` | JSON: index verdict, coverage state, Google canonical, last crawl |
| `gsc.py sitemaps SITE` | JSON: submitted sitemaps, errors, warnings |

Run `python3 scripts/gsc.py <cmd> --help` for all flags.

- `SITE` is the exact property string from `sites`: `sc-domain:example.com` or `https://example.com/`.
- Default window: 28 days ending 3 days ago (data lags 2–3 days).
- `--filter` repeats as AND. Operators: `equals`, `contains`, `notEquals`, `notContains`, `includingRegex`, `excludingRegex`.

## Common analyses

- Traffic drop: `--dimensions date` on two windows, then `--dimensions page` on both to find the pages that lost clicks.
- Quick wins: `--dimensions query,page --limit 1000`, keep position 5–20 with high impressions and low CTR.
- Page not indexed: `inspect` the URL, read `indexStatusResult.coverageState` and `googleCanonical`.

## Common mistakes

- Wrong property string: `example.com` fails, use the value from `sites`.
- Comparing windows of different length or including the last 2 days (incomplete data).
- Summing `ctr` or `position` across rows: recompute CTR as clicks / impressions; position is an average.
- `inspect` exits 1 with `HTTP 500` after 2 retries: Google fails some URLs on every call, while other URLs of the same property work. Report it, and suggest the Search Console UI for that URL.
- A `--dimensions date` query also lists days with 0 impressions; a page query with no traffic returns 0 rows. Neither is an error.
