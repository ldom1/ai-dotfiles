---
name: marketingpowers
description: Use when starting any marketing, promotion, launch, positioning, copy, SEO or growth task — routes to the right marketing skill and enforces the order they must run in. Trigger on "promote", "launch", "market this", "go-to-market", "GTM", "positioning", "ICP", "landing page copy", "Product Hunt", "backlinks", "directories", "vs page", "alternative page", "competitor comparison", "why would anyone buy this", "how do I get users", "growth", or any request to write or improve marketing material. Also the entry point when the user says "marketingpowers".
metadata:
  version: 1.0.0
---

# Marketingpowers

Six marketing skills, one entry point. This skill decides **which** one to run, in **what order**, and tells you when a request is not actually a marketing task at all.

## The Rule

**`product-marketing` runs first, before any other skill in this set.** It writes `.agents/product-marketing.md` — product, ICP, positioning, verbatim customer language — into the **target project's** repo. Every other skill in this set reads that file before acting.

Skip it and you get generic SaaS output: copy that could describe any tool, comparison pages that argue nothing, launch angles with no audience behind them. There is no version of "just this once" that produces good work here.

If `.agents/product-marketing.md` is missing when a downstream skill is requested, say so and run `product-marketing` first. If it exists but is thin or stale in the sections the requested skill depends on (see the table below), fix those sections first.

## Routing Table

| Skill | Reach for it when | Produces | Depends on these sections of the context doc |
|---|---|---|---|
| `product-marketing` | Always first. Also whenever positioning, audience or category changes. | `.agents/product-marketing.md` | — (it *is* the source) |
| `launch` | Something is about to ship publicly, or shipped and was never announced. | Launch plan, channel sequence, Product Hunt assets, post-launch cadence | Positioning, ICP, category |
| `copywriting` | A page has to persuade — home, landing, pricing, feature, README hero. | Page copy: headline, subhead, body, CTA | Verbatim customer language, pain points, differentiators |
| `directory-submissions` | You need discovery and backlinks without a budget. | Prioritized directory list, per-directory positioning variants, submission tracker | Category, one-liner, competitor set |
| `competitors` | Buyers are comparing you to a named tool, or searching "<tool> alternative". | `vs` and `alternative` pages, content architecture | Differentiators, competitor set, ICP |
| `marketing-psychology` | Copy or pricing is technically correct but doesn't move anyone. | Not a deliverable — a lens applied to another skill's output | Pain points, buying triggers |

## Invoking a Sub-Skill

The six live one level below this file, at `skills/<name>/SKILL.md` relative to this plugin's
root — where `<name>` is the exact name in the table above (`skills/product-marketing/SKILL.md`,
`skills/launch/SKILL.md`, and so on).

**In Claude Code** they are addressable directly as `marketingpowers:<name>` — invoke them and
stop reading here.

**In Cursor CLI and Mistral Vibe** they are *not*. Both discover skills one level deep, so they
see this router and nothing under it: `marketingpowers:<name>` resolves to nothing there, and
neither does a bare `<name>`. **Read the file at the path above instead** — reading it puts the
same instructions in context that invoking it would, and the routing and ordering rules in this
file still apply unchanged. If a `<name>` in the table is not in your available-skills list,
that is the situation you are in; go straight to the path, do not report the skill as missing.

## How to Use Each One

### `product-marketing` — the foundation
Not a strategy skill. It is a **context-document generator**, and its whole value is that it stops you re-deriving the same facts in every later task.

Two modes: auto-draft from the codebase (it reads README, landing copy, docs, package manifests) or a section-by-section interview. **Auto-draft first, then correct** — reviewing a wrong draft surfaces more than answering questions cold, and it is far faster.

Push hard for *verbatim* customer language. "It just lands in Notion, structured, in seconds" beats "streamlines knowledge capture" every time, and only the first one can be pasted into a headline.

Re-run it when positioning shifts. It versions the doc and keeps a changelog, so treat it as a living file, not a one-off.

### `launch` — the highest-leverage single event
Run it **before** you ship, not the week after. It has a readiness gate that will tell you to delay, and that verdict is worth more than the plan.

Best for: initial public launch, a feature big enough to re-announce the product, coming out of beta or a waitlist.

Not for: routine releases (a CHANGELOG entry is the correct amount of ceremony), or ongoing marketing after the launch window closes.

Its Product Hunt playbook is the most operationally detailed part. If you are not doing PH, still read the asset checklist — the same assets serve HN, Reddit and Show-and-tell posts.

### `copywriting` — for pages that must persuade
Give it one page at a time and say what that page's single job is. "Improve the site" produces mush; "make the hero explain what this is to someone who has never heard of it" produces something you can ship.

Use it on your README hero too. For an open-source tool the README *is* the landing page, and it is usually the worst-written marketing asset in the project because it was written for contributors, not evaluators.

Not for: email sequences, popup copy, or editing existing copy for tone — those are different upstream skills, not vendored here.

### `directory-submissions` — the zero-budget compounding channel
Highest ROI per hour of anything in this set when you have no budget, and the most boring. It covers directories, review sites, AI/agent/MCP registries, a GEO section on getting cited by LLMs, and a submission tracker so you don't lose track of 40 listings.

Read its "Three Hard Rules" before submitting anything — the failure mode is spraying a weak listing across 40 sites and burning first impressions you cannot retake.

Pair it with `competitors`: the backlinks need to point at pages worth landing on, and the comparison pages are usually the best target.

### `competitors` — positioning made concrete
Four formats: singular alternative, plural alternatives, you-vs-them, them-vs-them. Pick by search intent, not by what you want to say.

Reach for it when your differentiator is a *category* difference rather than a feature difference — self-hosted vs SaaS, open-source vs proprietary, one-tool vs suite. Those comparisons write themselves and rank, because the buyer is already searching the comparison.

Be honest in the tables. A comparison page that pretends you win every row destroys its own credibility and gets cited by LLMs as marketing rather than as a source.

### `marketing-psychology` — a lens, never a deliverable
15 thinking models and ~40 cognitive biases. It produces nothing on its own — its job is to be **applied to another skill's output**.

Use it when: copy is accurate but flat, pricing feels arbitrary, or a page describes features and the reader still doesn't act.

Do not run it first, and do not run it alone. "Apply marketing psychology to my product" is not a task; "the pricing page has three tiers and everyone picks the cheapest, look at the anchoring" is.

## Sequencing

For a product that has never been marketed, in order:

1. `product-marketing` — write the context doc
2. `copywriting` — fix the front door (README hero, landing page) so arrivals convert
3. `competitors` — build the pages that will catch comparison search
4. `launch` — plan and run the moment
5. `directory-submissions` — the backlink and discovery layer, pointing at 2 and 3
6. `marketing-psychology` — a pass back over 2, 3 and 4

Steps 2 and 3 come **before** 4 deliberately: a launch drives traffic to whatever exists, and a launch spike against a bad landing page is a spike you only get once.

The detailed ordered playbook, including the open-source dev-tool specifics, is in `references/campaign-sequence.md`.

## Red Flags

| Thought | Reality |
|---|---|
| "I'll write the copy first, the context doc after" | The context doc is the input to the copy. Backwards. |
| "The README is fine, it's for developers" | For an OSS tool the README *is* the landing page. |
| "Let's launch, then fix the site" | The launch spike is not repeatable. Fix the site first. |
| "Apply psychology to the product" | Psychology applies to a specific artifact, not to a product. |
| "Submit to every directory today" | A weak listing spent across 40 sites wastes 40 first impressions. |
| "We have no competitors" | Then no one is searching for a solution either. Find the status quo you replace. |
| "This needs a marketing plan" | Not vendored here. Route to `launch` for a moment, or answer directly. |

## Not a Marketing Task

Route away rather than forcing a fit:

- **Paid ads, cold email, sales decks, mobile app store listings, SMS, referral programs** — deliberately not vendored in this set. Say so and either answer directly or point at [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) for the upstream skill.
- **Technical SEO audits** — needs a real content site first. Fix the front door before auditing crawl depth.
- **"Is this a good idea"** — that is product discovery. Use `superpowers:brainstorming` or `grill-me`.
- **Writing the actual product** — that is engineering. Marketing skills describe what exists; they do not decide what to build.

## Provenance

The six skills under this plugin are vendored from [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) (MIT, © Corey Haines). The pin is `.marketingskills_version`. This router (`SKILL.md` and `references/`) is local and not upstream — re-syncing the six does not touch it.
