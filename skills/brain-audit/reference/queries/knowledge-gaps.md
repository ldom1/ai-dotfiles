# Q&A Query Template: Knowledge Gaps & Missing Articles

**Query Name:** Knowledge Gaps & Missing Articles

**Category:** Knowledge Base & Learning

## Purpose

Identify underrepresented knowledge areas in the vault, detect topics mentioned frequently but not documented thoroughly, and recommend high-impact articles to write. This helps ensure the Local Brain remains a comprehensive, up-to-date reference.

## Instructions for Claude

You are analyzing a Local Brain vault to identify knowledge coverage gaps. Your task is to:

1. **Survey current coverage:**
   - What are the main knowledge domains (Kubernetes, Python, AWS, etc.)?
   - How many articles does each domain have?
   - What's the age and recency of each domain?

2. **Identify frequently mentioned topics with weak coverage:**
   - What topics appear in daily notes/projects but lack detailed articles?
   - What terminology is used without clear definitions?
   - What patterns emerge that should be documented?

3. **Analyze knowledge clusters:**
   - Are there related topics that should link to each other?
   - Are there orphaned topics that could be merged or consolidated?
   - What foundation concepts are missing?

4. **Assess documentation quality:**
   - Which articles are outdated and need refreshes?
   - Which articles lack examples or practical guidance?
   - What topics have only surface-level coverage?

5. **Prioritize recommendations:**
   - What articles would have the highest impact?
   - What topics are needed soonest (based on active projects)?
   - What would strengthen the knowledge base most?

6. **Generate action plan:**
   - Specific article titles to write
   - Suggested outline for each
   - Estimated effort and priority

## Output Format

```markdown
# Knowledge Gaps & Missing Articles

## Coverage Overview
| Domain | Articles | Age | Status |
|--------|----------|-----|--------|
| Kubernetes | 12 | 2-8 weeks | Good |
| AWS | 8 | 2-16 weeks | Needs refresh |
| Python | 10 | 1-12 weeks | Good |
| [Domain] | [N] | [range] | [status] |

## High-Impact Missing Articles

### Tier 1 (Write This Week)
1. **[Title]**
   - Domain: [category]
   - Why needed: [impact/frequency analysis]
   - Suggested outline:
     - Introduction/overview
     - Key concepts
     - Best practices
     - Examples/case studies
   - Estimated time: [X hours]
   - Dependencies: [other articles to read first]

### Tier 2 (Write This Month)
[Similar format, lower priority]

### Tier 3 (Consider, Plan Ahead)
[Similar format, lower priority]

## Articles Needing Refresh
1. **[Title]**
   - Last updated: [date]
   - Issue: [what's outdated/missing]
   - Recommended changes: [specific improvements]
   - Estimated time: [X hours]

## Frequently Mentioned, Underdocumented Topics
1. **[Topic]**
   - Mentions: [N times in vault]
   - Current coverage: [brief summary]
   - Recommended article: [suggested outline]

## Knowledge Base Health Metrics
- Total articles: [N]
- Avg article age: [X weeks]
- Coverage completeness: [X%]
- Articles with 2+ cross-links: [X%]
- Articles updated this month: [X%]

## Recommendations & Action Plan
1. **[Priority 1]** Write [article title] — enables [X projects/use cases]
2. **[Priority 2]** Update [article title] — addresses [outdated section]
3. **[Priority 3]** Consolidate [topics] — reduce duplication
4. **[Priority 4]** Create [missing foundation article] — supports multiple domains
```

## Questions to Answer

1. **What knowledge areas are underrepresented?**
   - Which domains have few articles relative to project needs?
   - What topics are mentioned frequently but lack dedicated documentation?
   - What foundational concepts are missing?

2. **What articles would have the highest impact?**
   - Which would unblock the most projects?
   - Which would be referenced most frequently?
   - Which would reduce context-switching or ramp-up time?

3. **What's outdated and needs refreshing?**
   - Which articles are older than 3 months?
   - What's changed in covered topics (new best practices, versions, etc.)?
   - What articles have corrections or clarifications pending?

4. **What patterns should be documented?**
   - What repeating solutions appear in daily notes/projects?
   - What design patterns are used but not formally documented?
   - What "tribal knowledge" should be captured?

5. **How can we strengthen knowledge connections?**
   - Which topics should link to each other but don't?
   - What would benefit from a "topic overview" article?
   - What concepts depend on foundational understanding?

## Example Query Session

```
User: Run the "Knowledge Gaps & Missing Articles" query
Claude: I'll analyze your vault for coverage gaps...

[Claude reviews all articles, daily notes, projects, and connections]

Claude: Here's your knowledge gap analysis:

# Knowledge Gaps & Missing Articles

## Coverage Overview
| Domain | Articles | Age | Status |
|--------|----------|-----|--------|
| Kubernetes | 12 | 2-8 weeks | Good |
| Python | 10 | 1-12 weeks | Good |
| AWS | 8 | 2-20 weeks | Needs refresh |
| System Design | 5 | 4-16 weeks | Sparse |
| DevOps/Infrastructure | 6 | 3-10 weeks | Adequate |

## High-Impact Missing Articles

### Tier 1 (Write This Week)
1. **Kafka Consumer Groups & Offset Management**
   - Domain: Messaging/Streaming
   - Why needed: Referenced in 3 projects, CAP-streaming-platform blocked
   - Outline:
     - Consumer group concepts
     - Offset strategies (earliest, latest, specific)
     - Partition rebalancing
     - Common failure modes
   - Time: 2-3 hours
   - Dependencies: Must read "Kafka Architecture Overview" first

2. **Service Mesh Pattern Comparison: Istio vs Linkerd**
   - Domain: Architecture/DevOps
   - Why needed: CAP-service-mesh-migration decision pending
   - Outline:
     - High-level architectural differences
     - Performance/resource implications
     - Learning curve comparison
     - When to choose each
   - Time: 3-4 hours
   - Dependencies: "Kubernetes Networking Basics", "Sidecar Pattern"

### Tier 2 (Write This Month)
1. **AWS VPC Flow Logs Analysis** — current AWS articles missing observability
2. **Python Async Patterns Deep Dive** — used in 2 projects, covered shallowly
3. **Distributed Tracing with OpenTelemetry** — foundational for observability platform

## Articles Needing Refresh
1. **Kubernetes Best Practices**
   - Last updated: 8 weeks ago
   - Issue: Pre-1.27; missing latest API changes
   - Changes: Update examples for 1.28+, add new deprecations
   - Time: 1-2 hours

2. **AWS IAM Policies**
   - Last updated: 16 weeks ago
   - Issue: Pre-bedrock; doesn't cover new identity features
   - Changes: Add AWS IAM Identity Center section
   - Time: 2-3 hours

## Frequently Mentioned, Underdocumented Topics
1. **Circuit Breakers**
   - Mentions: 8 times in daily notes and projects
   - Current coverage: 1 sentence in Resilience Patterns article
   - Recommended: Dedicated article with implementation examples

2. **Event Sourcing**
   - Mentions: 6 times in architecture discussions
   - Current coverage: None; only mentions in other articles
   - Recommended: Full article with CAP-event-store case study

## Knowledge Base Health Metrics
- Total articles: 47
- Avg article age: 6 weeks
- Coverage completeness: 72%
- Articles with 2+ cross-links: 68%
- Articles updated this month: 15%

## Action Plan
1. **[HIGH]** Write Kafka Consumer Groups article — unblocks CAP-streaming-platform
2. **[HIGH]** Create Istio vs Linkerd comparison — needed for architecture decision
3. **[MEDIUM]** Update Kubernetes Best Practices for 1.28 — reduce technical debt
4. **[MEDIUM]** Create Circuit Breaker patterns article — used repeatedly
5. **[LOW]** Refresh AWS IAM article — proactive maintenance
```

## Tips for Best Results

- **Be quantitative:** Count mentions, measure article age, estimate impact
- **Connect to projects:** Show how knowledge gaps affect active work
- **Prioritize by impact:** Focus on articles that unblock multiple projects
- **Suggest outlines:** Make it easy to start writing by including structure
- **Include dependencies:** Note what foundation knowledge readers need
- **Measure health:** Track article age, freshness, and interconnectedness

## Frequency

- **Run weekly:** Part of Phase 3 Q&A in brain-audit
- **After major project milestones:** When new knowledge domains emerge
- **Quarterly deep dive:** Comprehensive refresh of all coverage metrics

## Integration with Writing

After identifying gaps:
1. Choose Tier 1 articles to write this week
2. Use the suggested outlines as writing templates
3. Link new articles to existing knowledge graph
4. Re-run query next week to verify gaps are closing
5. Archive results to track learning progress

---

**Last Updated:** 2026-04-11  
**Template Version:** 1.0
