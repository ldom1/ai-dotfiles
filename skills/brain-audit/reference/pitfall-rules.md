# Pitfall rules

How to write a rule in `pitfalls.md` or in a `*-patterns.md` note. `/capture` step 4 and `brain-audit:compile` both follow this file. It is the only place that holds these rules.

- Add one bullet under the matching `## <Topic>`: imperative rule + the mechanism in a clause, exact command when that is the fix. No dates, no project names, no narrative — the session log keeps the story.
- End the bullet with its id: the section letter and the next free number, e.g. `^g15`. Letters in `pitfalls.md`: `v` Verification, `d` Diagnosis, `u` Working with the user, `s` Safety and secrets. Letters in pattern notes: `g` git-patterns, `c` claude-code-patterns, `h` shell-patterns, `o` vault-patterns, `n` deployment, `l` llm. A rule keeps its id when it moves between files. Never renumber or reuse an id. A merge keeps the lower id and adds the other to `## Retired ids` as `^g7→^g2`. A rule that has a sensor carries `(sensor: <name>)` just before its id: `promote` writes it in "After it ships", and `count-pitfall-hits.py` reads it (`has_sensor`).
- After every edit, run `bash ~/ai-dotfiles/scripts/check-pitfalls-budget.sh`. The script enforces the 6,000 B cap of `pitfalls.md`. On exit 1, merge rules (Absorb) or move a stack section to a pattern note, then run it again. Do not finish while it fails.

  ```markdown
  - Check `git worktree list | grep "[<branch>]"` before checking out a branch — two worktrees on one branch move it under each other's files. ^g15
  - Compute forecast tables and gate thresholds with a script from the stated assumptions — hand-typed tables contradict their own rates. ^v12
  ```
