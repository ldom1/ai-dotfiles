---
name: audit-report
description: Last step of every securitypowers run — write the audit report (findings, what each step checked and why, what was not verified, next actions) in French, publish it as a private artifact when possible, and write generic learning notes for each security concept met, so the owner learns from every audit. Use at the end of any security review, scan or audit, or when the user asks for "le rapport", "la fiche d'audit", "explique-moi l'audit".
---

# Audit report and learning notes

Two outputs: a **report** (sensitive) and **learning notes** (generic). The owner uses both to learn security on their own projects.

## 1. The report

**Where.** `.agents/security-reports/YYYY-MM-DD-<scope>.md` in the target project.
- Before writing, make sure `.agents/security-reports/` is in the project `.gitignore` (add the line if missing). The report names hosts, ports and open findings: it is never committed.

**Language.** French. Keep tool names, rule ids, commands and code as they are.

**Sections, in this order:**

1. **Synthèse** — scope (repo, diff, hosts), date (UTC), egress point for network steps, tools and versions, profile state (`ok`, reviewed date), one verdict line **per step**: `rien trouvé`, `N findings`, `non exécuté (raison)`. No global verdict, never "conforme".
2. **Findings** — highest severity first, in the `owasp-security` format: title with CWE / OWASP / ASVS ids, location, path (input → sink), impact, fix, confidence, status (`corrigé`, `ouvert`, `accepté`).
3. **Comprendre l'audit** — one short section per step that ran:
   - *Ce que l'étape vérifie* (1-2 sentences);
   - *Pourquoi c'est important* — the attack it prevents, told as a concrete scenario on this project;
   - *Ce que le résultat veut dire* — how to read it, and its limits (what the tool cannot see);
   - *Pour aller plus loin* — one reference: OWASP Cheat Sheet, ASVS id, CWE, ANSSI rule, tool doc;
   - links to the learning notes of the concepts it touched.
4. **Ce qui n'a pas été vérifié** — skipped steps and why, `notchecked` rules, ASVS counts (`verified` / `failed` / `not applicable` / `not evaluated`), the blind spots of each tool.
5. **Prochaines actions** — ordered, each with an owner and a file or host.

**Publish.** A hosted artifact stores the report outside the machine. Publish it only when the profile says `external_data_allowed: true`, or when the owner says yes for this report. Otherwise the Markdown file is the deliverable. To publish, in Claude Code with the Artifact tool: load the `artifact-design` skill, build an HTML page from the report (same sections; findings as a table with severity colors; "Comprendre l'audit" as readable cards), and publish it **private**. Give the owner the link. In other harnesses, the Markdown file is the deliverable.

## 2. Learning notes

One note per **security concept** met in the run (examples: "IDOR", "clé munge Slurm", "TLS 1.0", "secret dans l'historique git", "fail-open").

**Where.** `$BRAIN_PATH/resources/knowledge/security/<concept-slug>.md` when `$BRAIN_PATH` is set; otherwise `.agents/security-learning/<concept-slug>.md` in the project.

**Generic only.** No host name, IP, path, port list or finding detail. A note must be safe to read by anyone. The project appears only as its slug.

**If the note exists,** read it and add only what is new (rewrite in place, never a dated section, never a duplicate note). Add the project slug to "Où je l'ai rencontré" if missing.

**Shape:**

```markdown
---
title: <Concept>
tags: [security, <category>]
---

# <Concept>

## Définition
## Pourquoi c'est un risque
## Comment ça s'exploite
## Comment s'en protéger
## Comment le détecter (outil, règle, commande)
## Où je l'ai rencontré
- [[<project-slug>]]
## Sources
- <OWASP / CWE / ANSSI / tool doc link>
```

Vault links are `[[slug]]` (filename only).

## Red flags

| Thought | Reality |
|---|---|
| "No findings, so a short report is enough" | "Comprendre l'audit" and "Ce qui n'a pas été vérifié" matter most when nothing was found. |
| "Put the open port list in the learning note as an example" | Learning notes are generic. Use a made-up example. |
| "Commit the report so the team sees it" | It maps the attack surface. Share the private artifact link instead. |
