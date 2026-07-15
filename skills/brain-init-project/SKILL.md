---
name: brain-init-project
description: Interactively initialise a project brain — read the vault note and project files, ask targeted questions, and write properly documented OBJECTIVES/DESIGN/ARCHITECTURE/DECISIONS/CONTEXT/ROADMAP/API files into .claude/memory/.
user-invocable: true
---

# brain-init-project

Populate a project's `.claude/memory/` knowledge files by gathering context from the vault, the project itself, and targeted questions to the user. Never overwrites a non-template file without asking.

## When to use

Run after `ai-dotfiles init <path>` has created the `.claude/memory/` folder structure. The init command creates template placeholders; this skill replaces them with real content.

Also run when a project brain exists but the files still contain only template boilerplate.

## Steps

### 1 — Locate the project

If a path was given as an argument, use it. Otherwise use the current git root. Confirm the project slug from `.brain-project`.

### 2 — Read available context (silently, do not narrate)

Read in this order — stop reading each source once you have enough signal:

1. **Vault one-pager** `$BRAIN_PATH/projects/<slug>.md` — goals, status, caps, roadmap section
2. **Existing brain files** `<project>/.claude/memory/*.md` — anything already written
3. **Project README** (root `README.md` or `docs/README.md`)
4. **Package manifest** — first match of `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `pom.xml`
5. **Top-level directory listing** — infer module structure

### 3 — Ask questions per file

For each knowledge file, present a **short summary of what you already know** from step 2, then ask only the gaps. Do not ask for information you already have. Ask one file at a time, not all at once.

#### OBJECTIVES.md
- What is the main goal of this project in one sentence?
- What does success look like? (measurable outcomes if possible)
- What is explicitly out of scope?

#### DESIGN.md
- What was the original application/product design?
- Who is the primary user, and what are the core workflows?
- Which design intent should remain reviewable over time, separate from live implementation details?

#### ARCHITECTURE.md
- What is the tech stack? (language, framework, key libraries)
- What are the top-level components and what does each do?
- Are there any non-obvious architectural decisions already made?

#### DECISIONS.md
- What are the most important decisions already made (with rationale)?
- What was considered and rejected?
*(Skip if no decisions have been made yet — leave template header only)*

#### CONTEXT.md
- What is done, what is in progress, what is blocked?
- What are the open questions or unresolved decisions?
- What should happen next?

#### ROADMAP.md
- What features or milestones are planned?
- What is the current priority order?
*(Skip if roadmap is covered in the vault one-pager — just reference it)*

#### API.md
- Does this project expose or consume external APIs/endpoints?
- What auth mechanism is used?
*(Skip entirely if the project has no external API surface)*

### 4 — Write the files

Write each file to `<project>/.claude/memory/<FILE>.md` using the gathered answers. Use the [template format](../../config/memory-templates/) as the base structure.

**Rules:**
- Never overwrite a file that already has substantive content (not just template placeholders) without explicitly asking the user first.
- Write concisely — respect the `<!-- keep this file under ~N words -->` budget in each template; these files are read by an agent at session start.
- Set the `updated:` frontmatter field to today's date whenever a file's content changes.
- Cross-link related files with markdown links instead of repeating content: a DECISIONS.md entry's **Affects** line should link to the ARCHITECTURE.md/ROADMAP.md section it changes; ROADMAP.md items should link back to the OBJECTIVES.md scope they serve.
- DECISIONS.md is append-only — if it already has entries, add new ones at the bottom, never delete.
- If the user says "skip" for a file, leave the template placeholder unchanged.

### 4b — Mirror to the vault (always, no need to ask)

After writing/updating any file(s) in `<project>/.claude/memory/`, immediately copy those same files to `$BRAIN_PATH/projects/<slug>/<FILE>.md`, overwriting the vault copy so it matches. This is a standard, automatic part of this skill — never ask the user whether to do it, and never skip it. Do this for every file touched in step 4, every time this skill runs (initial init and later updates alike).

### 4c — Create/update the vault one-pager (always, no need to ask)

Every project also needs `$BRAIN_PATH/projects/<slug>.md` — the single-file overview note, distinct from the `projects/<slug>/` detail folder. `init-project.sh` does not create this file, so this skill is responsible for it. Never ask whether to create it — always do it as a standard part of this process, on first init and again whenever memory files materially change.

- Use `$BRAIN_PATH/_templates/project-template.md` as the structural reference (frontmatter: `title`, `created`, `tags: [project]`, `caps`, `status`, `start`, `end`, `path`, `prod`; body sections: Objective, TL;DR, Description, Architecture, Roadmap, Proposed Improvements, Related Resources, Notes, Journal). That file is an Obsidian Templater script (not directly executable) — hand-write the rendered Markdown yourself following its structure, don't try to run it.
- `caps`: ask the user which CAP(s) apply if not already known (e.g. `[[caps/developer]]`, `[[caps/artelys]]`) — do not guess silently.
- Populate every section from the already-gathered OBJECTIVES/DESIGN/ARCHITECTURE/DECISIONS/CONTEXT/ROADMAP/API content — do not re-interview the user for content that lives there; synthesize and cross-link with `[[<slug>/FILE]]`-style links back to the detail files instead of duplicating full text.
- Append one line to the Journal section for this session's work instead of rewriting prior entries.
- If the one-pager already exists with substantive content, update it in place (sync new/changed facts) rather than overwriting wholesale — same non-destructive rule as step 4.

### 5 — Confirm and print next steps

After writing all files, print a one-line summary of what was written (confirming both the vault mirror from 4b and the one-pager from 4c) and remind the user:
- `CONTEXT.md` should be updated at the end of each session
- `brain-sync end` will push changes to the vault automatically

## Critical rules

- Never ask all questions at once — one file at a time keeps the conversation focused.
- Never silently skip a file — always tell the user which files were written and which were skipped.
- Never invent content — if you don't have enough context to fill a section, ask.
- The interview happens in the chat conversation, not via shell prompts.

## Files

```
skills/brain-init-project/
├── SKILL.md
└── skills/brain-init-project/
    └── SKILL.md  → ../../SKILL.md
```
