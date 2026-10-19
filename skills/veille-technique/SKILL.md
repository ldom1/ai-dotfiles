---
name: veille-technique
description: Use when the user shares links, repos, articles or tools from AI / agent tech watch and wants them compared with one of their projects — "veille", "veille techno", "regarde ce repo", "compare à mon harness", "gap analysis", "ça vaut le coup d'intégrer ?" — or asks to audit a project's own skills, hooks and rules ("audit des skills", "qu'est-ce qui est redondant ?"). Not for a plain explanation of one tool with no comparison.
user-invocable: true
---

# veille-technique

Router. Goal: one reviewed verdict per component, compared with what the target project already does, and — only on approval — an integration plan. Facts over inference: every claim carries a source URL or `path:line`, or the label `inférence`.

| User says | Subskill |
|-----------|----------|
| "veille", "regarde ce repo / cet article", "ça vaut le coup d'intégrer ?", "compare à mon harness" | `veille` |
| "audit des skills", "qu'est-ce qui est redondant / cassé / obsolète ?", "note mes skills" | `audit` |
| a new element must be compared **precisely** with the target (same layer: review skill vs review skills, memory tool vs memory layer) | `audit` scoped to that layer, then `veille` with the audit artifact as baseline |

Each subskill is `skills/<name>/SKILL.md` under this skill's root (`~/ai-dotfiles/skills/veille-technique/`). Claude Code exposes them as `veille-technique:<name>`; Cursor CLI and Mistral Vibe only see this router, so read the file at that path instead — don't report the subskill as missing.

The steps below are shared. A subskill replaces only its own **Analyse** step.

Gates: stop at the end of steps 0, 3 and 4. Never chain them.

## 0. Cadrage — gate

`grill-me` style: one question at a time, a recommended answer each, skip a question the user already answered.

1. **Mode.** `veille`, `audit`, or `audit` then `veille` (third table row).
2. **Target project.** Recommend the current one: `bash ~/ai-dotfiles/skills/brain-load/scripts/load.sh --slug-only`. Several targets are allowed (e.g. a personal harness and an enterprise kit); each gets its own fit column.
3. **Question behind the request.** What the user hopes to gain, and any hard constraint (no MCP, no new dependency, EU hosting, …).

Restate the three answers in one line, then stop.

## 1. Baseline (read-only)

```bash
BP=$(grep -m1 '^BRAIN_PATH=' ~/ai-dotfiles/config/brain.env | cut -d= -f2 | tr -d '"')
sed -n '1,80p' "$BP/projects/<slug>.md"                          # idea, how it works
ls <repo>/.claude/memory/ 2>/dev/null && sed -n '1,60p' <repo>/.claude/memory/CONTEXT.md
grep -n '^|' <repo>/README.md | sed -n '1,40p'                   # skill / feature table
grep -n '<slug>' "$BP/resources/knowledge/veille-technique.md"   # past verdicts for this target
```

Then run `brain-search` with the component names: a past verdict or prompt on the same item changes the analysis.

## 2. Analyse

Follow the subskill. Both produce one block per component in this shape, ≤ 300 words, sourced:

```markdown
## <composant>
**Mécanisme :** what it does and where it runs (hook, skill, MCP, CLI, service). Not marketing.
**Affirmations vs preuves :** each measured claim with its source and measurement conditions; unmeasured claims labelled.
**Coût :** install, dependencies, tokens, maintenance, lock-in, licence.
**Déjà couvert par :** <existing skill / hook / rule of the target>, or "rien".
**Écart :** what it does that the target does not.
**Conflit :** which existing mechanism it duplicates or contradicts.
```

Verify one claim per source yourself before synthesis (pitfall ^v10): a README promise or a `WebFetch` paraphrase is not a measurement. Fetch the raw file for the exact wording.

## 3. Rapport (artifact, en français) — gate

Load `artifact-design`, then publish one HTML artifact in French (icon `report`). Title: `Veille <sujet> <YYYY-MM-DD>` (the main source or theme, e.g. `Veille Firecrawl 2026-10-19`) or `Audit <slug> <YYYY-MM-DD>`: two runs on the same day must not share a title. Sections, in this order:

1. **Verdict** — one table row per component: `Composant | Verdict | Plus petit changement | Cible | Effort S/M/L`. Verdict vocabulary comes from the subskill.
2. **Par composant** — the step-2 block, plus the fit: which target and which layer (règle, skill, hook, capteur, MCP).
3. **Transversal** — overlaps between components, and what they say together about the target.
4. **Questions ouvertes** — what blocks a verdict.
5. **Sources** — numbered URLs or `path:line`.

Give the URL and ask the user to review. Stop. Apply review comments to the artifact (same `file_path`) until the user approves the verdicts.

## 4. Trace — gate

Append one row per component to `$BP/resources/knowledge/veille-technique.md` (create it with the header on first use):

```markdown
| Date | Composant | Verdict | Cible | Artifact |
|---|---|---|---|---|
| 2026-10-19 | pstack `why` | Adapter | ai-dotfiles | <url> |
```

Ask: "Plan d'intégration pour les composants retenus ?" Stop. **No**, or nothing to integrate: done.

## 5. Plan d'intégration

**REQUIRED SUB-SKILL:** `superpowers:writing-plans`. Save the plan in the vault, not in `docs/`: `$BP/inbox/daily/plans/<target-slug>/<YYYY-MM-DD>-<topic>-plan.md`. Scope it to the **Plus petit changement** column. New dependency: ask first. Code follows `ponytail`; prose follows the docs style in `AGENTS.md`.

## Done when

- The artifact URL is in chat and the user approved the verdicts.
- The ledger has one row per component.
- Either the user declined a plan, or the plan file exists in the vault.

## Common mistakes

- Analysing the source before the baseline: produces "new" features the target already has.
- Repeating the source's own numbers ("90% fewer tokens") without the measurement conditions.
- Writing the plan into the artifact: the artifact is the analysis; the plan lives in the vault.
- One verdict per source instead of per component: a repo often holds one Adopter and ten Ignorer.
