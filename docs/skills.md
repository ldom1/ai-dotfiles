# Skills

The skills of ai-dotfiles: the catalogue, the vendored upstreams, and how each tool finds them. Back to the [README](../README.md).

## Install a skill

The marketplace publishes these plugins (`.claude-plugin/marketplace.json`). The other skills below reach your machine through `install.sh`.

```
/plugin marketplace add ldom1/ai-dotfiles
/plugin install brain-sync@ldom1-ai-dotfiles
/plugin install brain-load@ldom1-ai-dotfiles
/plugin install grill-me@ldom1-ai-dotfiles
/plugin install veille-technique@ldom1-ai-dotfiles
/plugin install finops-audit@ldom1-ai-dotfiles
/plugin install graphify@ldom1-ai-dotfiles
/plugin install git-promotion@ldom1-ai-dotfiles
/plugin install python-tests@ldom1-ai-dotfiles
/plugin install search-console@ldom1-ai-dotfiles
/plugin install why@ldom1-ai-dotfiles
```

| Skill | Purpose |
|-------|---------|
| [brain-sync](https://github.com/ldom1/ai-dotfiles/wiki/Skills/Brain-Sync) | Sync Local Brain Obsidian vault (Claude Code hooks; Cursor CLI via `cursor-agent-brain.sh` alias; manual via skill) |
| [brain-load](https://github.com/ldom1/ai-dotfiles/wiki/Skills/Brain-Load) | Load / instantiate project notes from vault |
| [brain-search](https://github.com/ldom1/ai-dotfiles/wiki/Skills/Brain-Search) | Semantic + keyword search over vault via qmd (`scripts/search.sh`) |
| [brain-audit](https://github.com/ldom1/ai-dotfiles/wiki/Skills/Brain-Audit) | Four-phase vault maintenance (raw → digest) |
| capture | End-of-session workflow: session log, project memory snapshot, cross-project pitfall rules, sync |
| grill-me | Stress-test plans through one-question-at-a-time design interrogation |
| veille-technique | Router over two sub-skills: `veille` (external sources vs a target project; Adopter / Adapter / Surveiller / Ignorer) and `audit` (the target's own skills, hooks and rules; Garder / Réviser / Fusionner / Retirer). `audit` on one layer can run first as the exact baseline of a `veille`. Output: a reviewed French artifact, a ledger row per component in the vault, an optional integration plan |
| why | Before changing code: history of a range (`git log -L`, `git blame`, merged PRs via `gh`, vault notes) → `Préserver` / `Changer` / `Éviter` / `Risque`, each bullet cited by commit, PR or note (`/why <file>:<range>`). Idea from pstack `why`, MIT |
| git-promotion | Promote develop → preprod → main (or a PR straight onto main) with a semver tag and GitHub Release; stages, tag prefix, gate and changelog per repo in `.git-promotion.json` |
| ponytail | Lazy senior mode — YAGNI ladder, stdlib before deps, minimum code that works (`/ponytail`) |
| implement-with-cursor-agent | Experimental, evaluated on one plan: same quality as Claude alone, about 2× the wall time. Use it to keep long implementation work off the Claude usage window (lean review mode). Claude runs a validated vault plan through headless Cursor agents (`gpt-5.3-codex`). Each agent runs in a container with no GitHub credentials and commits locally. Needs a Cursor API key in `~/.config/cursor-agent/api-key` (mode 600). Claude reviews hard, then opens a project PR against the integration branch (`develop`, or the first `.git-promotion.json` stage) and a vault note PR. It squash-merges into that branch and never merges or promotes onto `main` |
| asd-ste100 | Rewrite a doc in ASD-STE100 Simplified Technical English (strict or STE-flavored), with a stdlib linter (`scripts/ste-lint.py`) |
| benchmark-checklist | Vet a perf measurement before you report it: limiter, tuning, errors, repeatability, relevance (`/benchmark-checklist`, user-invoked only) |
| sop-builder | Turn process notes into validated seven-section SOP documents |
| photo-archive-triage | Non-destructive photo/video triage: exact dedup, corrupt screening, capture-date recovery |
| python-tests | Test-first Python playbook: red, green, full suite, lint, then `mutate.py` checks that each new test kills a mutant |
| [server-audit](https://github.com/ldom1/ai-dotfiles/wiki/Skills/Server-Audit) | Infra audit: parallel checks and JSON reports |
| [graphify](https://github.com/ldom1/ai-dotfiles/wiki/Skills/Graphify) | `/graphify` — folder → knowledge graph; also [graphify.net](https://graphify.net/) |
| [finops-audit](https://github.com/ldom1/ai-dotfiles/wiki/Skills/FinOps-Audit) | Weekly token spend review → vault |
| search-console | Read-only Google Search Console: queries, pages, CTR, position (TSV), URL inspection, sitemaps. Stdlib script `scripts/gsc.py`, your own OAuth client in `~/.config/gsc/` |
| marketingpowers | `/marketingpowers` — router over six marketing sub-skills; enforces `product-marketing` first and the order the rest run in |
| orca-cli / orca-computer-use / orchestration | Stubs that load the version-matched guide from the local Orca CLI (`orca skills get <name>`): worktrees and terminals, GUI control of a visible window, Orca worker agents. Need the [Orca](https://github.com/stablyai/orca) app installed |

`graphify` is vendored from [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) (the `SKILL.md` + `reference/` files, adapted with two local additions: the `GRAPHIFY_PROJECT` local-clone fallback and default-on agent-MCP auto-wiring via `scripts/setup_agent_mcp.py`). The synced upstream release is tracked in `skills/graphify/.graphify_version` — re-diff against that tag before syncing again to isolate local customizations from upstream changes.

`marketingpowers` is a **router plugin**: `skills/marketingpowers/SKILL.md` decides which marketing sub-skill to run and in what order, and `references/campaign-sequence.md` holds the ordered full-campaign playbook. Both are local, not upstream.

The six sub-skills under `skills/marketingpowers/skills/` — `product-marketing`, `launch`, `copywriting`, `directory-submissions`, `competitors`, `marketing-psychology` — are vendored from [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) `v2.11.37` (MIT, © Corey Haines) — `SKILL.md` + `references/` only; upstream `evals/` fixtures dropped. They surface as `marketingpowers:<name>`. Single shared pin for all six: `skills/marketingpowers/.marketingskills_version`. One local patch: the `../../tools/integrations/introw.md` link in `launch/SKILL.md` is rewritten to an absolute upstream URL at the pinned tag (the partner `tools/` tree is not vendored). Re-syncing the six does not touch the router.

| Sub-skill | Purpose |
|-----------|---------|
| product-marketing | Product/ICP/positioning context doc (`.agents/product-marketing.md`) — **runs first**; every other sub-skill reads it |
| launch | Launch planning: ORB framework, readiness gate, Product Hunt playbook, post-launch cadence |
| copywriting | Landing/home/pricing page copy — frameworks, hero structure, CTA and value-prop work |
| directory-submissions | Directory + review-site layer of a launch: backlinks, GEO, destination pages, submission tracker |
| competitors | `vs` / `alternative` comparison pages for SEO and positioning |
| marketing-psychology | Mental models + cognitive biases as a lens for copy, pricing and offers — never a deliverable on its own |

`product-marketing` writes `.agents/product-marketing.md` into the **target project** repo, not into ai-dotfiles. Paid ads, cold email, sales decks, mobile app-store listings, SMS and referral programs are deliberately **not** vendored.

**Cross-harness caveat.** Nested sub-skills resolve only in Claude Code, as `marketingpowers:<name>`. Cursor CLI and Mistral Vibe discover skills one level deep, so they load the router and nothing beneath it. Both routers (`marketingpowers` and `brain-audit`) therefore document the relative `skills/<name>/SKILL.md` path and instruct the agent to read the file directly when the namespaced form is unavailable — reading it puts the same instructions in context that invoking it would.

**Pitfall-to-sensor promotion.** `/capture` writes a `**Pitfall hit:** [[pitfalls#^<id>]]` line in the session log for each Absorb or Improve verdict. `/brain-audit` runs `promote` after `compile`. It counts distinct sessions per rule id in the lookback window (`skills/brain-audit/scripts/count-pitfall-hits.py BRAIN_PATH [--days N]`). It writes a sensor draft to `inbox/sensors/` for each id hit in 2 sessions or more. It also groups `fix`/`Revert` commits of the repos in `config/brain-projects.tsv` into mistake classes, and drafts a sensor only for a class with a proof. The digest lists the drafts. Nothing installs itself: you accept a draft by asking for it as a normal task.

`ponytail` is vendored from [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) (`skills/ponytail/SKILL.md` only — on-demand skill, not the upstream alwaysApply Cursor rule). Pin: `skills/ponytail/.ponytail_version`. Re-sync: diff against the pinned tag, apply upstream, bump the pin (same pattern as graphify; no local patches today). The upstream `ponytail-review` / `-audit` / `-debt` / `-gain` / `-help` sub-skills are not vendored.

`asd-ste100` is vendored from [danyuchn/asd-ste100-skill](https://github.com/danyuchn/asd-ste100-skill) (MIT): `SKILL.md`, `references/`, `examples/`, `scripts/ste-lint.py`, `LICENSE`. It ships no copy of ASD's dictionary (not redistributable). Upstream has no releases, so the pin `skills/asd-ste100/.ste100_version` is a commit SHA and `config/vendored-skills.json` tracks `"branch": "master"`: the update check compares the pin to the branch head. The always-on part of the docs style is the `## Docs style (ASD-STE100 inspired)` block in `AGENTS.md`; this skill is the on-demand rewrite pass.

`benchmark-checklist` is vendored from [cursor/plugins](https://github.com/cursor/plugins) (MIT, © 2026 Lauren Tan): `pstack/skills/benchmark-checklist/SKILL.md` and `pstack/LICENSE`, copied verbatim with no local patch. The skill is user-invoked only (`disable-model-invocation`). Pin: `skills/benchmark-checklist/.pstack_version`, a commit SHA of the whole repo. It is not in `config/vendored-skills.json`. The update check compares the pin to the repo head. `cursor/plugins` moves daily, so it would warn every session. The playbooks it names (Opening a PR, Perf issue, Hillclimb) belong to pstack and are not vendored; ignore them. Re-sync: clone at a new SHA, `diff` the file, copy it, bump the pin.

`orca-cli`, `orca-computer-use` and `orchestration` are vendored from [stablyai/orca](https://github.com/stablyai/orca) (MIT): `skills/<name>/SKILL.md` and `LICENSE`, copied verbatim with no local patch. They are discovery stubs: the real guide comes from the installed Orca binary, so it matches its version. On Linux outside an Orca terminal, they call `orca-ide`, never bare `orca` (the GNOME screen reader). Pin: `skills/<name>/.orca_version`, the commit SHA of release `v1.4.255`. They are not in `config/vendored-skills.json`: Orca releases about once a day, so the check would warn every session. Re-sync: clone at a new SHA, `diff` the three files, copy them, bump the three pins.

### Vendored skill update checks

SessionStart (Claude + Cursor Agent CLI) runs `scripts/check-vendored-skill-updates.sh`: compares pins in `config/vendored-skills.json` to each repo’s GitHub **latest release** (cache: `~/.claude/cache/vendored-skill-updates.json`, default **24h**, fail-open). Fetches run in parallel (shared 3s budget). If a pin is behind, a short WARNING is injected into session context and appended to `.claude/logs/vendored-skill-updates.log`. Transient fetch failures do not freeze the cache for a full day (short retry TTL).

This does **not** auto-upgrade — alert only. Re-sync stays manual (diff pin→tag, replace `skills/<name>/`, bump pin, CHANGELOG, `install.sh`). Register new upstreams in `config/vendored-skills.json`. Force refresh: delete the cache file, then start a session or run `bash scripts/check-vendored-skill-updates.sh --inject`.

Wiki hub: **[Skills](https://github.com/ldom1/ai-dotfiles/wiki/Skills)** (catalogue). Keep wiki pages directly in the local **`.wiki/`** clone (GitHub wiki repo) under the **`Skills/`** namespace (e.g. `Skills/Brain-Sync`), then publish explicitly with:

```bash
# one-time setup:
git clone https://github.com/ldom1/ai-dotfiles.wiki.git .wiki

# publish:
bash scripts/update-wiki.sh
```

**Full documentation → [Wiki](https://github.com/ldom1/ai-dotfiles/wiki)**

---

## Frontend & design skills

Six design/frontend skills are available by default, from two different mechanisms:

| Skill | Mechanism | Source | Role |
|-------|-----------|--------|------|
| `impeccable` | Plugin (`impeccable`) | [pbakaus/impeccable](https://github.com/pbakaus/impeccable), successor to Anthropic's `frontend-design` | Production-grade UI code for real apps — 59 deterministic anti-pattern detectors plus a live-browser polish/audit/critique loop (`/impeccable polish`, `/impeccable audit`, etc.), aimed squarely at generic "AI slop" output. Installs a `PostToolUse`(Edit\|Write)+`Stop` hook that scans touched UI files every session (Node ≥22 required; self-disables with a message otherwise, never blocks a turn on error). |
| `taste-skill` | Plugin (`taste-skill`) | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill), third-party | 14 bundled skills for opinionated, committed style directions (brutalist, minimalist, soft, redesign, stitch, image-to-code, image-gen variants) — pick a direction directly instead of combinatorially picking from a lookup table. |
| `web-artifacts-builder` | Local skill (`skills/`) | Vendored from [anthropics/skills](https://github.com/anthropics/skills) | Bundles a multi-component React + Tailwind + shadcn/ui build into a single self-contained HTML artifact. Use for interactive claude.ai artifacts. |
| `canvas-design` | Local skill (`skills/`) | Vendored from `anthropics/skills` | Static visual art — posters, social graphics, cover images — as PDF/PNG, via a "design philosophy first" workflow. |
| `algorithmic-art` | Local skill (`skills/`) | Vendored from `anthropics/skills` | Generative/procedural art via p5.js — flow fields, particle systems, fractals, seeded randomness. |
| `mcp-builder` | Local skill (`skills/`) | Vendored from `anthropics/skills` | Guide for building well-designed MCP servers (Python/FastMCP or Node/TS SDK) that expose external services as tools. |

**Why they're complementary, not redundant:** `taste-skill` supplies an opinionated style direction; `impeccable` and `web-artifacts-builder` turn that direction into working UI code (a real app vs. a self-contained artifact, respectively) and catch generic-looking output along the way; `canvas-design` and `algorithmic-art` cover static and generative *visual art* rather than UI — different output shape (PDF/PNG image) than the code-producing skills; `mcp-builder` is orthogonal — it's for building MCP servers, not visual output. Claude picks the matching skill from the task's output shape.

*Replaced `frontend-design` + `ui-ux-pro-max` with `impeccable` + `taste-skill` (2026-08-25): both complaints driving the swap — generic "AI slop" output and too much manual palette/font-pairing lookup — are exactly what `impeccable`'s anti-pattern detectors and `taste-skill`'s committed style directions target.*

**Two enablement mechanisms, deliberately:**
- `impeccable` and `taste-skill` are registered as Claude Code **plugins** via `extraKnownMarketplaces` in `.claude/settings.json.tpl` (merged into `settings.json` by `scripts/install.sh`), but **disabled globally**: their skill listings and impeccable's per-edit hook cost context in every non-UI session. Enable them per frontend project in its `.claude/settings.json` (committed) or `.claude/settings.local.json` (personal) — project settings override user settings:
  ```json
  { "enabledPlugins": { "impeccable@impeccable": true, "taste-skill@taste-skill": true, "vercel@claude-plugins-official": true } }
  ```
- `web-artifacts-builder`, `canvas-design`, `algorithmic-art`, and `mcp-builder` are vendored as **local skills** under `skills/<name>/SKILL.md`, cherry-picked from Anthropic's `example-skills` plugin (which bundles 17 skills — `docx`, `pdf`, `webapp-testing`, `theme-factory`, etc. — most unwanted here). `scripts/install.sh` auto-symlinks any `skills/<name>` with a `SKILL.md` into `.claude/skills/`, `.vibe/skills/`, and `.cursor/skills/`, so no plugin/marketplace entry is needed for these four, and no unwanted skills come along for the ride. See "Skill discovery across tools" below for how that linking works.

To pick these up on a machine that already ran `install.sh` before this change: `git pull && bash scripts/install.sh` (idempotent — resymlinks `skills/`, regenerates `settings.json` from the template). You don't have to remember this yourself — the `SessionStart` hook (`brain-session-start.sh`) compares `settings.json` against `settings.json.tpl` on every session and re-runs `install.sh` automatically if only plugins or marketplaces are behind, logging to `.claude/logs/brain-load.log`. For new permissions, `env` or hooks it only prints `[install-check] template adds: <keys>`: run `install.sh` yourself. New plugins from an auto-heal become active starting the *next* session, since Claude Code reads `settings.json` before the hook runs; local skills under `skills/` are picked up as soon as `install.sh` resymlinks them.

### Skill discovery across tools

Every skill under `skills/<name>/` is symlinked by `scripts/install.sh` into three per-tool directories — `.claude/skills/<name>`, `.vibe/skills/<name>`, `.cursor/skills/<name>` — one flat loop, same rule for all three: link it if `skills/<name>/SKILL.md` exists, skip it if the name matches `coe-*`.

`coe-*` is reserved for internal/company skills synced locally by a separate, gitignored `scripts/sync-coe-skills.sh` — never committed to this repo (`skills/coe-*`, `.claude/skills/coe-*`, `.vibe/skills/coe-*`, `.cursor/skills/coe-*` are all in `.gitignore`). The `install.sh` filter keeps them out of all three tools' runtime view too, not just out of git — a `coe-*` skill present locally is invisible to Claude Code, Vibe, and Cursor alike until the exclusion is deliberately lifted.

(Prior to this, `install.sh`'s skill loop had no `coe-*` filter at all — `.claude/skills`/`.vibe/skills` linked every skill unconditionally, and `.cursor/skills` was a single symlink to the whole `skills/` directory. `coe-*` was kept out of git via `.gitignore`, but a `coe-*` skill present locally was fully visible to all three tools at runtime. The filter above is what actually enforces the exclusion now, for all three.)

### Private skills

Keep a skill out of this public repo, but share it across your machines, with a private git repo cloned into `private/` (gitignored):

```bash
git clone <your-private-repo> ~/ai-dotfiles/private   # holds skills/<name>/SKILL.md
bash ~/ai-dotfiles/scripts/install.sh
```

- `install.sh` links each `private/skills/<name>` into `.claude/skills/`, `.vibe/skills/` and `.cursor/skills/`.
- Each of those directories gets an untracked `.gitignore` that lists the private links and ignores itself. The public repo never tracks or names a private skill.
- A private skill with the same name as a public `skills/<name>` is skipped with a warning.
- After a `git pull` in `private/` that adds a skill, run `install.sh` again.
- Moving a skill from `skills/` to `private/` does not remove it from the public git history.


Invocations append to `~/.claude/skill-usage.log` (`date skill [source]`):

| Source tag | When |
|------------|------|
| *(none)* / `claude:Skill` | Claude Code `Skill` tool (`PreToolUse` → `.claude/hooks/log-skill-usage.sh`) |
| `claude:sessionStart` / `cursor:sessionStart` / … | Hook-driven `brain-sync` / `brain-load` via `scripts/log-skill-usage.sh` |
| `cursor:skill-read` | Cursor Agent `preToolUse`/`Read` of a `**/skills/**/SKILL.md` (heuristic — exploratory reads count too) |

**Not counted:** alwaysApply `.mdc` rules, SessionStart prompt injection, memory-only follow-through, Vibe (its hooks do not log skill use). Cursor counts are approximate; do not delete skills from Cursor lines alone.

B0 observation artifacts: `spikes/cursor-b0-*` (logger + live sample).

---

## Security review & pentesting skills

| Skill | Mechanism | Source | Role |
|-------|-----------|--------|------|
| `find-security-vulnerabilities-in-code` | Local skill (`skills/`) | Vendored from [usestrix/strix](https://github.com/usestrix/strix) | White-box AI security review — reads the source, then exploits what it finds in a Docker sandbox so every reported issue has a working proof-of-concept, not a static-analysis guess. Only invoke against a local path/repo you own; the SKILL.md itself gates on this — see below. |
| `fix-security-vulnerabilities-with-strix` | Local skill (`skills/`) | Vendored from `usestrix/strix` | Triage Strix findings by severity, patch the root cause, re-run Strix to prove the fix actually closes the exploit. |

Both wrap the [Strix](https://github.com/usestrix/strix) open-source CLI (Apache-2.0) — install separately with `curl -sSL https://strix.ai/install | bash` or `pipx install strix-agent`; requires Docker and an `STRIX_LLM`/`LLM_API_KEY` pair. Strix's own README disclaims unauthorized use but doesn't enforce it at runtime — it will point real exploit execution at whatever target string it's given. `find-security-vulnerabilities-in-code`'s SKILL.md adds an explicit gate on top: only run against a local path or a repo you own, and stop to confirm authorization if a bare external hostname/domain/IP is named instead.

Only these 2 of Strix's 9 upstream skills are vendored — the rest ([usestrix/strix/skills](https://github.com/usestrix/strix/tree/main/skills)) are either thinner wrappers around the same engine or cover per-project decisions (CI PR-gating, the managed app.strix.ai cloud) that don't belong in a shared dotfiles skill set. Read the upstream repo directly if a specific project wants one of those.
