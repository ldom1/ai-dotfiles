# Campaign Sequence

The ordered playbook behind the routing table in `SKILL.md`. Read this when running a full campaign rather than a single task.

## Phase 0 — Context (`product-marketing`)

**Run inside the target project's repo**, not inside ai-dotfiles. The output lands at `.agents/product-marketing.md` next to the code it describes.

Auto-draft from the codebase, then correct. Feed it anything the project already has — existing marketing docs, decks, promo assets, a CRM readiness audit — rather than letting it draft cold from the README alone. A project with prior marketing artifacts usually has better language buried in them than the README ever had.

Gate before moving on: can you answer, in the product's own words, *who* it is for, *what shelf* it sits on, and *what they say* when they describe the problem? If any of the three is still yours rather than a customer's, the doc is not done.

## Phase 1 — Front door (`copywriting`)

Fix what arrivals actually see, in this order:

1. **README hero** — first three lines above the badges. For an open-source tool this is the highest-traffic marketing copy in the project and almost always the worst, because it was written for contributors.
2. **Landing page or web UI first screen** — whatever a non-contributor lands on.
3. **Pricing / licensing clarity** — including "free and self-hosted" as an explicit positive claim, not an absence of a price.

One page per invocation, and state that page's single job.

## Phase 2 — Comparison surface (`competitors`)

Pick formats by search intent:

- `<incumbent> alternative` — highest intent, lowest effort, build first
- `<you> vs <incumbent>` — for the one competitor buyers actually name
- `alternatives to <incumbent>` (plural) — broader, ranks slower, build once the singular ones work

Category-level differences are the strongest material: self-hosted vs SaaS, open-source vs proprietary, one focused tool vs a suite. Feature-level comparisons age badly and invite a feature race.

Keep the tables honest. Rows where the competitor wins buy credibility for the rows where you do, and LLMs increasingly cite honest comparisons while discounting self-promotional ones.

## Phase 3 — The moment (`launch`)

Pass the readiness gate before picking a date. If the gate says delay, delay — the plan is worth less than that verdict.

Sequence within the launch window:

1. Assets (demo, screenshots, one-liner, FAQ) — reused across every channel
2. Owned channels first (mailing list, existing users)
3. The anchor event (Product Hunt, or HN Show if PH does not fit)
4. Community posts, staggered — never the same day across every subreddit
5. Post-launch cadence, so the spike does not become the whole story

## Phase 4 — Discovery layer (`directory-submissions`)

Run *after* phases 1–2, so the backlinks point at pages worth landing on. Point them at the comparison pages and the fixed landing page, not at the bare repo.

Read the Three Hard Rules first. Track submissions in the provided tracker — 40 listings across review sites, AI/agent/MCP registries and startup directories is unmanageable from memory, and duplicate or abandoned submissions cost you the listing.

## Phase 5 — Revision pass (`marketing-psychology`)

Go back over the copy, the comparison pages and the launch messaging with a specific bias or model in hand. Name the artifact and the problem: "the pricing page anchors on the cheapest tier", "the hero asks for a decision before establishing the category".

Not a phase you can run without phases 1–4 having produced something to revise.

---

## Open-source dev tool specifics

Applies when the product is a self-hosted or open-source developer tool with no ad budget and no sales motion.

**What works, roughly in ROI order**

1. **The launch moment** — Product Hunt, HN Show, and the one or two subreddits where the tool's *users* already are (not where developers are in general).
2. **Comparison pages against the SaaS incumbent** — "self-hosted alternative to X" is a search with real intent and almost no competition from the incumbents themselves.
3. **Directories and registries** — especially AI/agent/MCP registries, which are new enough that listings still rank.
4. **The README as a landing page** — free, already the highest-traffic surface, usually unoptimized.
5. **Build-in-public content** — sustained, slow, compounds. Not vendored here (`social` upstream covers it).

**What does not work at this scale**

Paid acquisition of any kind, cold outreach, events, and technical SEO audits before there is content to audit. All deliberately excluded from this set.

**The self-hosted positioning trap**

"Self-hosted" and "your data never leaves your server" are the differentiators, but they are *features of a category*, not benefits. The buyer's actual motivation is usually one of: a compliance requirement, distrust of a specific vendor, cost at scale, or wanting the thing to keep working when a SaaS shuts down. Find which one applies to your ICP in phase 0 and lead with that instead of with the architecture.
