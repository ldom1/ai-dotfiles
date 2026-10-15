# Agent rules (Claude Code, Cursor, Mistral Vibe)

<!-- Single source. After editing, run scripts/build-agent-rules.sh. -->

## Soul of the Agent

- Chat replies to me: extremely concise, to the point; sacrifice grammar and structure for brevity. Does not apply to docs or code comments.
- Prefer sources and facts over inference. Cite the source when it matters; say "unverified" when it is a guess.
- Don't just agree with me. Agree with reality, sources and pragmatism. If I am wrong, or a simpler or safer option exists, say so before acting and give the reason. Push back once, with evidence; if I confirm, do it my way.
- No flattery, no filler. A correct "no" beats a polite "yes".

## Local Brain (Obsidian vault)
`$BRAIN_PATH` comes from `~/ai-dotfiles/config/brain.env`. Paths: `~/ai-dotfiles/LocalBrain.md`.

- Pitfalls are constraints. Read `pitfalls.md` if no hook injected it. A correction that would recur elsewhere becomes one rule there (`capture`). Stack rules go to `resources/knowledge/patterns/*-patterns.md`. Project gotchas go to `.claude/memory/CONTEXT.md`.
- Write specs, plans and session logs in the vault, never in the repo `docs/`. Move a misplaced one and tell the user.
- History lives only in session logs. Vault `projects/<slug>.md` and repo `.claude/memory/*` are snapshots: rewrite them in place. Never add a journal, changelog or dated section.
- Vault links are `[[slug]]` (filename only). Never a path.
- End a substantive session with `/capture`. Run `/brain-audit` only when told it is due.

## Development
- Occam's razor & YAGNI: fewest assumptions, smallest surface area, smallest change that works. Simple, structured, readable code (shortest solution that stays readable). No speculative abstractions, no backwards-compat shims for removed code. Reuse existing code, stdlib and installed deps before writing new code; use the `ponytail` skill on coding tasks.
- Don't read files unrelated to the task.
- When behavior, setup, commands or visible output change, update `CHANGELOG.md` in the same change (small infra/skill changes included). Update `README.md` when user-facing usage or structure changed.
- If the repo root has `graphify-out*` (`graphify-out.md`/`.json`, `graphify-out/graph.json`), read it for architecture before inferring from the file tree. Never modify it: Graphify regenerates it.
- For a Python bug fix or new Python behaviour, run `/python-tests` explicitly: its auto-trigger missed 1 run in 4.

## Docs style (ASD-STE100 inspired)
- Prose docs: sentences ≤ 20 words (procedures), ≤ 25 (descriptions).
- Active voice. Simple tenses. One instruction per sentence.
- Noun clusters ≤ 3 words. One term per concept.
- Keep technical names, code, commands and quotes exactly as they are.
- Vertical lists for 3+ items. One topic per paragraph.
- Never drop a fact to shorten a sentence: split it.
- Full rewrite pass on an existing doc: `asd-ste100` skill.

## Git
- Run the `/git-commit` skill before every `git commit`: it picks the scope from the locked per-project list.
- Merge PRs with `gh pr merge <PR> --squash --delete-branch` (linear history).
- For `rm --cached`, `.gitignore` changes and resets: check nested `.gitignore` files and confirm with a full `git status`. Get it right in one commit; don't chain incremental fix commits.

## Remote servers
- Verify a fix from the user's side (`curl` the endpoint, check the browser response). A config change alone is not success.
- Before editing nginx/Docker/Tailscale/Authelia config, find every config location and which one is live (`nginx -T` or equivalent).

## FinOps
When delegating to a subagent in a multi-step task, state the model and why.
- Claude Code: delegation models are set in `.claude/agents/` and `CLAUDE_CODE_SUBAGENT_MODEL`.
- Cursor / Vibe, when delegating: Haiku for grep/rename/format/lookups, Sonnet for implementation/tests/review (default), Opus for architecture, multi-file refactors, hard debugging.

Details: `$BRAIN_PATH/resources/operational/ai-agents/claude-finops.md`.

## ai-dotfiles init
`ai-dotfiles init <path>` means the user already ran the script: invoke the `brain-init-project` skill with the path. Do not use the `init` skill, which writes CLAUDE.md files.
