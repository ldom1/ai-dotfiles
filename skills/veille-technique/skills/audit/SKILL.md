---
name: audit
description: Use when a project's own skills, hooks, rules, plugins or MCP config must be inventoried and scored — "audit des skills", "qu'est-ce qui est redondant / cassé / obsolète ?", "note mes skills" — or when a tech-watch comparison needs an exact baseline of one layer first.
---

# audit

**REQUIRED BACKGROUND:** the router `~/ai-dotfiles/skills/veille-technique/SKILL.md` holds the shared steps (cadrage, baseline, rapport, trace, plan). Read it first if it is not in context. This file replaces its step 2 only.

Verdicts: **Garder** · **Réviser** (fix in place) · **Fusionner** (into a named component) · **Retirer**.

Read-only: no file is created, modified or deleted during the audit. Every finding cites `path:line`; a finding you could not verify from the filesystem is marked `[non vérifié]`.

## Scope

From step 0: the whole project, or one layer named by the user (review skills, memory layer, hooks, MCP). When the audit feeds a `veille`, scope it to the layer the new element belongs to.

## Inventory

```bash
cd <repo>
find skills -maxdepth 2 -name SKILL.md | sort
for f in skills/*/SKILL.md; do echo "=== $f ($(wc -w < "$f") words)"; sed -n '1,8p' "$f"; done
grep -h '^description:' skills/*/SKILL.md | awk '{ print length": "$0 }' | sort -n
find .claude/skills .cursor/skills .vibe/skills -type l ! -exec test -e {} \; -print   # broken links
grep -rnoE '[A-Za-z0-9_./-]+\.(md|sh|py|json)' skills/*/SKILL.md | sort -u             # referenced files
for d in skills/*/; do echo "$(git log -1 --format=%ad --date=short -- "$d") $d"; done | sort
ls .claude/hooks/ 2>/dev/null; jq '.hooks | keys' .claude/settings.json 2>/dev/null
jq -r '.plugins[].name' .claude-plugin/marketplace.json 2>/dev/null
```

Check every referenced path with `test -e`. A missing file is a `Réviser` finding on its own.

## Score

More than 10 components: dispatch one read-only `general-purpose` subagent per 10 (Sonnet), tools limited to `Read`, `Grep`, `Glob`, `Bash` read-only commands. Each returns the router's component block per item, with these readings:

| Field | Audit reading |
|---|---|
| **Mécanisme** | what the skill does, where it runs, what it dispatches |
| **Affirmations vs preuves** | does the body do what `description` says; do referenced paths, scripts, flags exist (`path:line`) |
| **Coût** | words loaded per invocation; always-on (rule, hook) or on demand |
| **Déjà couvert par** | overlapping skill, native Claude Code capability, MCP server, or vendored upstream |
| **Écart** | what the description promises and the body lacks |
| **Conflit** | contradiction with another skill, rule or pitfall; stale model id, date or path |

Add one line `**Note :** T S D C R P` with 1–5 scores: Triggering (description states when), Structure (≤ 500 lines, one reference level), Determinism (repeated work in a script), Currency, Redundancy, Portability (Claude Code / Cursor / Vibe).

## Output

Same artifact as the router's step 3, title `Audit technique <sujet> <YYYY-MM-DD>` (`<sujet>` rule in the router). The **Verdict** table is ordered by severity over effort: broken references and non-triggering skills first, style last. The **Transversal** section names patterns that touch 3+ components.

When the audit precedes a `veille`, hand the artifact URL to it as baseline and stop after step 4.

## Common mistakes

- Scoring from the description alone: read the body and test the paths.
- Flagging a vendored skill's upstream choices as local defects: check the pin file (`.<name>_version`) and diff against the tag first.
- Proposing a merge without naming the surviving component and the lines that move.
