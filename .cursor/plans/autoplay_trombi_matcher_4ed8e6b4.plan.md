---
name: Autoplay Trombi Matcher
overview: Build a minimal Python autoplay tool that uses browser session cookies to access the protected game API, derives image-name→person mapping from the wiki trombinoscope page, and auto-selects the correct answer in the live game UI.
todos:
  - id: deps
    content: Add minimal Python dependencies for HTTP parsing and browser automation
    status: completed
  - id: wiki-map
    content: Implement wiki scraper to build normalized image-key to name mapping
    status: completed
  - id: api-auth
    content: Load exported browser cookies and authenticate against game API
    status: completed
  - id: resolver
    content: Match game photoUrl keys to wiki mapping with strict-first fallback
    status: completed
  - id: autoplay
    content: Automate in-browser answer selection using resolved name
    status: completed
  - id: docs
    content: Document cookie export, run command, and known limitations
    status: completed
isProject: false
---

# Autoplay image-to-name matcher

## What I confirmed
- Game frontend loads protected endpoints: `/api/me`, `/api/employees`, `/api/game/token`, `/api/results`, `/api/leaderboard`.
- The game question uses employee fields `photoUrl`, `firstName`, `lastName`, and displays choices from those objects.
- The wiki page exposes image file references and adjacent full names in HTML table rows.

## Implementation approach
- Add one Python script in [main.py](/home/lgiron/artelys_ds_lab/trombinoscope_matcher/main.py) that does both mapping + autoplay.
- Build a deterministic `image_key -> {first_name,last_name,full_name}` map from wiki HTML:
  - Parse `<img src=...media=organisation:trombinoscope:<file>>` and paired name cells.
  - Normalize keys (lowercase, strip extension, unify separators `_`/`-`/spaces).
- Read session cookies from an exported Netscape cookie file (user browser export), then call game API:
  - `GET /api/me` (validate auth)
  - `GET /api/employees` (get `photoUrl` + names used by the game)
- Compute resolver map from game data:
  - Extract image key from each employee `photoUrl`.
  - Match with wiki keys (exact normalized match first, then conservative fallback rules).
- Autoplay loop with Playwright:
  - Open `https://trombi.artelys.lan/`, inject cookies, reload.
  - Detect current photo element (`img` in game card), extract key from its `src`.
  - Resolve expected first/last name (mode-aware: prénom vs nom mode).
  - Click matching answer button text.
- Keep minimal CLI options:
  - `--cookies <path>` (required)
  - `--mode first|last|auto` (default auto)
  - `--dry-run` (log guess without click)

## Minimal safeguards
- Fail fast on unauthorized cookies.
- Log unresolved image keys (for manual additions if naming mismatches exist).
- Stop if no candidate button matches expected name.

## Validation
- Verify successful `/api/me` and non-empty `/api/employees`.
- Test one manual round in `--dry-run`, then one live round with click enabled.
- Report unresolved keys and match rate after a short run.

## Files to touch
- [main.py](/home/lgiron/artelys_ds_lab/trombinoscope_matcher/main.py)
- [pyproject.toml](/home/lgiron/artelys_ds_lab/trombinoscope_matcher/pyproject.toml) (add minimal deps)
- [README.md](/home/lgiron/artelys_ds_lab/trombinoscope_matcher/README.md) (usage + cookie export steps)
- [CHANGELOG.md](/home/lgiron/artelys_ds_lab/trombinoscope_matcher/CHANGELOG.md) (new autoplay matcher entry)