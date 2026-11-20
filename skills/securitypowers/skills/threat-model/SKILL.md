---
name: threat-model
description: Short STRIDE threat model of a project from its security profile — assets, entry points, trust boundaries — with each threat ranked and given a mitigation or an accepted risk. Use for a new project, a new exposed service or a big architecture change, or when the user says "threat model", "STRIDE", "what could go wrong", "attack surface".
---

# Threat model (STRIDE)

Short and concrete. One page beats a framework nobody reads.

## Preconditions

`bash <plugin>/scripts/profile-check.sh <project>` prints `ok`. The profile gives assets, hosts, ports and entry points.

## Steps

1. **Draw the data flow in text.** Actors (user, admin, job script, external API), processes, data stores, and every trust boundary (Internet → reverse proxy, portal → scheduler, user job → shared filesystem).
2. **Walk STRIDE per boundary crossing:**

   | Letter | Threat | Ask |
   |---|---|---|
   | S | Spoofing | Can someone pretend to be another user or service here? |
   | T | Tampering | Can data or code be changed in transit or at rest? |
   | R | Repudiation | Could an action happen with no log tying it to someone? |
   | I | Information disclosure | Can data leak to someone who should not see it? |
   | D | Denial of service | Can one actor exhaust a shared resource (CPU, queue, disk)? |
   | E | Elevation of privilege | Can a user become admin, or a job escape to the host? |

3. **Rank** each threat: likelihood (who can do it, how hard) × impact (which asset). High / Medium / Low, one line of reason.
4. **Decide** for each: existing control (cite it), mitigation to add (concrete change), or accepted risk (add it to the profile's "Accepted risks").
5. **Name the checks** that verify the controls: which securitypowers step (scan, review, hardening rule) covers each one. A threat with no check is a gap: say so.

## Output

For `audit-report`: the data flow, the ranked threat table, and the gap list.

## Red flags

| Thought | Reality |
|---|---|
| "List every STRIDE item for every component" | Walk boundary crossings only. That is where threats live. |
| "Mitigation: follow best practices" | Name the change, the file or the config key. |
