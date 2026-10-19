---
name: promote
description: >-
  Counts how often each pitfall rule was hit in recent session logs and drafts
  a sensor (hook, stop check, lint rule or test) for each rule hit in two or
  more sessions. It also groups `fix`/`Revert` commits of the repos in `config/brain-projects.tsv` into mistake classes, and drafts a sensor only for a class with a proof. Writes drafts to inbox/sensors/ and never installs anything.
  Use when: "draft sensors", "turn recurring pitfalls into hooks", "which rules keep recurring", or
  after compile in a full brain-audit.
user-invocable: true
---

# brain-audit:promote

A rule that holds most of the time wants to be a sensor. This step finds the rules that recur and drafts their sensors. The user reviews each draft. Nothing installs itself. Vault references are `[[slug]]` wikilinks.

## 1 — Count

`/capture` step 4 writes one `**Pitfall hit:** [[pitfalls#^v3]]` line per Absorb or Improve verdict. Run the counter:

```bash
source ~/ai-dotfiles/skills/brain-audit/scripts/_brain_env.sh
python3 ~/ai-dotfiles/skills/brain-audit/scripts/count-pitfall-hits.py "$BRAIN_PATH" --days "${BRAIN_AUDIT_LOOKBACK_DAYS:-30}"
```

The script maps retired ids to their current id (`## Retired ids` in `pitfalls.md`). It counts distinct session logs per id. It marks an id `candidate` at 2 sessions or more. It marks `skip` an id that has a draft in `inbox/sensors/` or a `(sensor: …)` suffix on its rule. If it prints `0 candidates`, go to step 1b.

## 1b — Repo history

Fix and revert commits record mistakes that no session log names. List them for each registered repo:

```bash
source ~/ai-dotfiles/skills/brain-audit/scripts/_brain_env.sh
tail -n +2 ~/ai-dotfiles/config/brain-projects.tsv | cut -f2 | while read -r p; do
  [ -e "$p/.git" ] || continue
  echo "== $p"
  git -C "$p" log --no-merges --since="${BRAIN_AUDIT_LOOKBACK_DAYS:-30} days ago" --format='%h %s' -E --grep='^(fix|Revert)'
done
```

Group the subjects into mistake classes. A class seen twice, in any repo, is a `candidate`. Name each class and list its SHAs. Skip a class if a draft already holds one of its SHAs:

```bash
grep -l <sha> "$BRAIN_PATH"/inbox/sensors/*.md
```

If step 1 and step 1b found no candidate, report the counts and stop.

## 2 — Draft

For each pitfall `candidate` from step 1, read its rule (the line ending with `^<id>` in `pitfalls.md` or a `*-patterns.md` note) and its citing logs. Write `inbox/sensors/YYYY-MM-DD-<slug>.md` with:

```markdown
---
date: YYYY-MM-DD
type: sensor-draft
pitfall: ^v3
---

# Sensor draft: <slug>

**Rule:** <the rule text>
**Cited in:** pitfall id: [[log-1]], [[log-2]] | repo class: <repo> <sha>, <sha>, …
**Kind:** PreToolUse hook | Stop check | lint rule | pytest | not mechanizable (<reason>)
**Installs at:** <file or setting where it would live>
**Proof:** pitfall id: ran <cmd> on match/not_match: <result> | repo class: fails on <sha>, passes on HEAD: <cmd> | not mechanizable: none

## Draft (≤ 40 lines)
<code>

## Examples
- match: <input the sensor must catch>
- not_match: <input the sensor must let through>
```

Pick the kind whose guarantee you can state exactly. If no sensor can check the rule, write `not mechanizable` with the reason and no code. The `pitfall:` field is how the counter finds the draft later, so keep it.

Write a draft for a repo-history class too, with `pitfall:` set to a short kebab-case class name. Keep one form per slot.

- Noise filter: grouping commit subjects is a judgment call. A repo class becomes a draft only with a proof SHA.
- No proof: report the class under `Candidates without proof` and write no draft.
- `not mechanizable` is only for a rule that no sensor can check. Never use it for an unproven class.
- Repo class: list all its SHAs in `**Cited in:**`. The SHA grep finds the draft by them.
- Repo class proof: fails on the past SHA, passes on HEAD.
- Run the proof read-only: feed the sensor `git -C <repo> show <sha>:<path>`, or `git -C <repo> diff <sha>~1 <sha>`. HEAD means that repo's HEAD. Never check out, stash or reset a registered repo.
- Pitfall id proof: run the draft code on the `match` and `not_match` examples. Name the command and the result, with no SHA.
- A `not mechanizable` draft has no code and writes `**Proof:** none`.
- Drafts written before 2.1.0 have no Proof line. Leave them as they are.

## 3 — Report

```
brain-audit:promote complete
  Window: N days · ids with hits: N
  Candidates: N · drafts written: N · skipped (draft or sensor exists, classes included): N
  Repo classes: N · with proof: N · without proof: N
  Drafts: [[YYYY-MM-DD-<slug>]], …
  Candidates without proof: <class> (<sha>, …)
```

The user accepts a draft by asking for it as a normal task. After it ships, add `(sensor: <hook name>)` before the rule's id in `pitfalls.md`. A rule with a sensor is a merge candidate when the budget is tight.
