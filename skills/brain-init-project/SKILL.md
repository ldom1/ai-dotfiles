---
name: brain-init-project
description: Interactively initialise a project brain — read the vault note and project files, ask targeted questions, and write properly documented OBJECTIVES/DESIGN/ARCHITECTURE/DECISIONS/CONTEXT/ROADMAP/API files into .claude/memory/.
user-invocable: true
---

# brain-init-project

Replace the template placeholders that `ai-dotfiles init <path>` (`scripts/init-project.sh`) copied into `<project>/.claude/memory/` with real content, and write the vault one-pager. Also use it when a project's memory files still hold only boilerplate. These files are read by agents at session start, so write them for an agent: terse, current state, one fact per line.

## 1 — Gather context (silently)

Project = the path argument, else the git root; slug = first line of `.brain-project`. Read, stopping once you have enough signal:

1. Vault note `$BRAIN_PATH/projects/<slug>.md`
2. Existing `<project>/.claude/memory/*.md`
3. `README.md` (root or `docs/`), the package manifest (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `pom.xml`), the top-level tree

## 2 — Interview, one file at a time

For each file: summarise what you already know, then ask only for the gaps. One file per message keeps answers focused; the interview happens in chat, never via shell prompts. If you can't fill a section from context or answers, ask — don't invent. "skip" leaves the template untouched.

| File | Ask about | Skip when |
|---|---|---|
| `OBJECTIVES.md` | one-sentence goal, measurable success, explicit non-goals | — |
| `DESIGN.md` | original product intent, primary user, core workflows, durable constraints | pure library/infra |
| `ARCHITECTURE.md` | stack, top-level components and their job, data flow, invariants | — |
| `DECISIONS.md` | decisions already made and why | nothing decided yet |
| `CONTEXT.md` | what is live, in flight, blocked; open questions | — |
| `ROADMAP.md` | planned work in priority order | — |
| `API.md` | exposed/consumed endpoints, auth | no external API surface |

## 3 — Write `<project>/.claude/memory/`

Base structure: `~/ai-dotfiles/config/memory-templates/`. `init` copies every template except `DESIGN.md` and `API.md`. When the interview needs one (see the table in step 2), first copy it from `~/ai-dotfiles/config/memory-templates/on-demand/` to `<project>/.claude/memory/`, if the file is not there yet. Respect each template's `<!-- keep under ~N words -->` budget and set `updated:` to today on every change. These are snapshots rewritten in place — the history lives only in session logs (`inbox/daily/implementation/<slug>/`), so no journal, changelog or dated-entry sections:

- `CONTEXT.md` sections: `Live now`, `In flight`, `Blockers / open questions`, `Gotchas`, `Recent history` (≤ 5 `[[session-log]]` links).
- `DECISIONS.md`: one line per live decision, `- **<decision>** — <why> (<date>)`; a superseded decision is replaced, not appended to.
- `ROADMAP.md`: `Now` / `Next` / `Later` / `Open debt`.
- Link between memory files with relative markdown links (`[Key Modules](ARCHITECTURE.md#key-modules)`) rather than repeating content.

Ask before overwriting a file that already has real content (not just placeholders).

The vault mirror `projects/<slug>/` is kept in sync by `scripts/sync-project.sh` at every `brain-sync start`/`end` for projects in `config/brain-projects.tsv` (`init-project.sh` registers them). If the project is not registered, run `bash ~/ai-dotfiles/scripts/sync-project.sh <project-path>` once.

## 4 — Write the vault one-pager `projects/<slug>.md`

Always create or refresh it (`init`/`upgrade` create the skeleton via `skills/brain-load/scripts/instantiate.sh`: that heredoc is the canonical shape, so read it there and do not copy it from here). It is the project's **clear description**, printed at session start: someone who has never seen the repo should understand what it is, why it exists and what success looks like. ≤ 450 words, rewritten in place.

Fill the skeleton's sections from the interview: the one-sentence summary, Idea, Objectives, How it works, Where, Memory and Links. Keep deep architecture in `ARCHITECTURE.md`. Set `status` (`draft`/`active`/`paused`/`concluded`), `repo` and `prod` in the frontmatter.

No current-state or history sections: current state is `CONTEXT.md`, history is the session logs — that is what keeps the note from drifting. `caps`: ask which CAP(s) apply if unknown (`[[developer]]`, `[[Artelys]]`); don't pick one silently.

## 5 — Report

One line listing files written and files skipped (with reason), plus the vault note. Remind the user that `/capture` refreshes `CONTEXT.md` at session end and `brain-sync end` pushes the vault.
