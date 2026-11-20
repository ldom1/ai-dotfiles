---
name: exposure-scan
description: Check what a deployed host really exposes to the Internet — scan its open ports from outside with nmap, compare them with the profile's expected ports, and check TLS on each TLS port with testssl.sh. Only on targets the owner listed as authorized. Use when the user asks "which ports are open", "is MariaDB reachable from the internet", "scan my server from outside", "check TLS", or after a firewall or deployment change.
---

# Exposure scan

Answers one question: **what can an attacker on the Internet reach?** A scan from inside the host's network answers a different question.

## Target rules (no exception)

1. `uv run --script ../../scripts/profile-check.py <project>` (path relative to this file) prints `ok`.
2. The target appears **literally** in `authorized_targets` (host name or IP) **with scope `exposure-scan`** in its `Scope` column. No ranges, no CIDR, no wildcards. Anything else: refuse and say why.
3. Resolve the name (`getent ahosts <name>`). Every resolved IP (IPv4 and IPv6) must be one of the pinned IPs in the profile. A resolved IP that is not pinned: stop and tell the owner (DNS changed, or wrong host).
4. Scan the **pinned IPs**, each one, not the name.
5. Print the exact target list (name, IPs, port ranges, tools) and **ask the owner to confirm** before the first packet.
6. Redirects, discovered hosts, new subdomains and other IPs seen in results never extend the authorization.
7. Before the first write, add `.agents/security-reports/` to the project `.gitignore` if the line is missing: raw outputs map the attack surface.

## Where the scan runs from

- Record the egress point: `curl -s https://ifconfig.me` (public IP of the scanning machine), plus date and time (UTC).
- If the egress IP is inside the target's network, say the result does not show Internet exposure.
- A corporate network may block outbound ports: a port reported `filtered` may be open from elsewhere. Prefer a neutral machine (a VPS, a home server) for the final check, and say which one ran.

## Scans

Raw outputs go to `.agents/security-reports/raw/<date>/`. For each pinned IP (add `-6` for an IPv6 address):

1. TCP, all ports, connect scan (no root needed), open ports only:
   `nmap -Pn -sT -p- --open -T4 -oX <raw>/nmap-tcp-<ip>.xml <ip>`
2. Expected ports, all states (so "filtered" and "closed" are visible for the ports the profile says are public):
   `nmap -Pn -sT -p <expected-public-ports> -oX <raw>/nmap-expected-<ip>.xml <ip>`
3. Service versions on open ports only:
   `nmap -Pn -sT -sV -p <open-ports> -oX <raw>/nmap-sv-<ip>.xml <ip>`
4. Optional UDP top ports (needs root; ask): `sudo nmap -Pn -sU --top-ports 50 -oX <raw>/nmap-udp-<ip>.xml <ip>`
5. TLS on each TLS port: `testssl.sh --quiet --ip <ip> --jsonfile <raw>/testssl-<ip>-<port>.json <name>:<port>` (the name gives SNI; `--ip` keeps the scan on the pinned IP).

Tools missing: install from the distro (`nmap`) or use the official testssl.sh image; print versions.

## Compare

| Result | Meaning |
|---|---|
| Open, in `expected_ports` as public | Expected. Check version and TLS. |
| Open, in `expected_ports` as private | **Finding**: a private service is reachable from outside. |
| Open, not in `expected_ports` | **Finding**: unknown exposure. |
| Expected public, closed | Service down or not listening: report, not a security finding. |
| Filtered | Not proven closed. Say so, and from where the scan ran. |

Typical HPC findings: slurmctld/slurmd/slurmdbd (6817-6819), munge, LDAP 389/636, MariaDB 3306, Grafana 3000, Dex 5556 open to the Internet.

## Fix

The fix is a firewall or bind-address change in the IaC repo (`iac-scan` checks it). Never change the firewall on the host by hand.

## Output

For `audit-report`: egress IP, date, targets, tool versions, table of open ports vs expected, TLS grades and issues.
