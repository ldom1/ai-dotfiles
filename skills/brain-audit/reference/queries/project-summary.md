# Q&A Query Template: Project Progress Summary

**Query Name:** Project Progress Summary

**Category:** Project Management & Tracking

## Purpose

Analyze the state of all active projects in the vault, assess progress toward milestones, identify blockers and risks, and provide actionable recommendations for the week ahead.

## Instructions for Claude

You are analyzing a Local Brain vault containing active projects documented as Context Artifacts (CAPs). Your task is to:

1. **Review all projects** in the `projects/` directory
   - Extract project status from README.md or STATUS.md
   - Note milestone dates and completion percentages
   - Identify any documented blockers or risks

2. **Assess progress metrics:**
   - What percentage of each project is complete?
   - Which projects made the most progress this week/month?
   - Which projects are behind schedule?

3. **Identify blockers and risks:**
   - What are the top 3 blockers across all projects?
   - Which projects have design decisions pending?
   - What external dependencies are at risk?

4. **Analyze team workload:**
   - Are there projects with insufficient attention?
   - Are there projects nearing completion that need final push?
   - Do any projects need resource reallocation?

5. **Generate recommendations:**
   - Prioritize next week's work
   - Suggest actions to unblock stalled projects
   - Recommend design reviews or architectural decisions needed

## Output Format

```markdown
# Project Progress Summary

## Overview
- Total active projects: [N]
- Projects on schedule: [N]
- Projects at risk: [N]
- Avg completion: [X%]

## Top Performers (Most Progress This Week)
1. **[Project Name]**
   - Status: [X% complete]
   - Key achievement: [what was accomplished]
   - Next milestone: [upcoming goal]

## At Risk (Behind Schedule or Blocked)
1. **[Project Name]**
   - Status: [X% complete]
   - Blocker: [what's blocking progress]
   - Recommended action: [how to unblock]

## Design Decisions Pending
1. **[Project Name]** — [Decision topic]
   - Impact: [what's blocked by this decision]
   - Recommendation: [suggested path forward]

## Top Recommendations
1. **[HIGH PRIORITY]** [Specific action] — impacts [projects]
2. **[MEDIUM PRIORITY]** [Specific action] — impacts [projects]
3. **[LOW PRIORITY]** [Specific action] — impacts [projects]

## Detailed Project Status

### [Project Name]
- **Status:** [X% complete, on/ahead/behind schedule]
- **Last update:** [date]
- **Key milestones:** [upcoming milestones with dates]
- **Blockers:** [any blockers or risks]
- **Next steps:** [what needs to happen next week]

[Repeat for each project...]

## Workload Analysis
- Projects needing attention: [list]
- Projects ready for closure: [list]
- Recommended reallocation: [any suggestions]
```

## Questions to Answer

1. **Which projects are making the best progress?**
   - List top 3 by velocity/completion percentage this week
   - What patterns do successful projects share?

2. **Which projects are stalled or at risk?**
   - Why are they behind? (blockers, resource constraints, unclear requirements)
   - What's the immediate action to unblock them?

3. **What are the most critical blockers?**
   - Design decisions, dependencies, or external factors?
   - Who owns each blocker and what's the timeline to resolve?

4. **Do we have team alignment on priorities?**
   - Is current work aligned with stated project priorities?
   - Are any projects being neglected?

5. **What should we focus on next week?**
   - Prioritized list of actions by impact
   - Resource allocation recommendations
   - Milestones to celebrate or prepare for

## Example Query Session

```
User: Run the "Project Progress Summary" query
Claude: I'll analyze your projects. Let me check the vault...

[Claude reviews projects/ directory, CAPs, and status documents]

Claude: Here's this week's project summary:

# Project Progress Summary

## Overview
- Total active projects: 5
- Projects on schedule: 3
- Projects at risk: 2
- Avg completion: 52%

## Top Performers
1. **CAP-streaming-platform**
   - Status: 60% complete, ON SCHEDULE
   - Achievement: Completed Kafka integration + topic design
   - Next: Consumer groups implementation

2. **CAP-infrastructure-automation**
   - Status: 30% complete, AHEAD OF SCHEDULE
   - Achievement: Terraform modules scaffolding complete
   - Next: AWS provider integration

## At Risk
1. **CAP-api-gateway-v2**
   - Status: 45% complete, BEHIND SCHEDULE (2 weeks)
   - Blocker: Authentication design pending security review
   - Action: Schedule urgent design review with security team

2. **CAP-service-mesh-migration**
   - Status: 20% complete, AT RISK due to vendor licensing questions
   - Blocker: Licensing decision between Istio/Linkerd
   - Action: Escalate licensing decision to PM

## Recommendations
1. **[HIGH]** Unblock API Gateway auth review — impacts 2 downstream projects
2. **[MEDIUM]** Finalize service mesh vendor decision — affects architecture
3. **[LOW]** Document Kafka patterns for team reference
```

## Tips for Best Results

- **Be specific:** Include project names, completion percentages, and concrete blockers
- **Prioritize:** Rank recommendations by impact and urgency
- **Analyze patterns:** Look for systemic issues (e.g., all projects blocked on architecture reviews)
- **Connect to strategy:** Tie recommendations to broader business/team goals
- **Include next steps:** Don't just identify problems; suggest concrete actions and owners

## Frequency

- **Run weekly:** Typically Sunday evening or Monday morning
- **As needed:** When major project milestone approaches or blocker is escalated
- **Archive:** Store results in `resources/queries/archive/` for trend analysis

---

**Last Updated:** 2026-04-11  
**Template Version:** 1.0
