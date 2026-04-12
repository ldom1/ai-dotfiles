# Notion → Brain layer routing

Use with **`$BRAIN_PATH`** from `brain.env` / `BRAIN_ENV_FILE` (see `brain-sync` / `brain-load`). This table is a default map—always prefer existing vault conventions and the user’s explicit targets.

| Kind of content | Layer | Typical targets |
|-----------------|-------|-----------------|
| Identity, always-on goals, session-hot pointers | **L1** | `IDENTITY.md`, `breadcrumbs.md` |
| Area stance, long-horizon responsibility | **L2** | `caps/<id>.md` |
| Reference, patterns, SOPs, external knowledge | **L2** | `resources/knowledge/...`, `resources/` |
| Active project summary, status, links | **L3** | `projects/<slug>.md` |
| Session / implementation narrative, commands, decisions | **L3** | `index/implementation/<slug>/YYYY-MM-DD-topic.md` |
| Deep specs, ADRs, plans | **L3** | `resources/knowledge/architecture/...`, project note sections |
| Superseded or frozen material | **L3** | `archive/`, `archive/processed/` if used |

**L1 edits:** require **explicit user confirmation** before changing the file.

**Not in the Brain:** raw daily workflow stays in Notion; only compile **decisions, patterns, milestones** into the vault.
