---
name: server-audit
description: Run a robust server health audit locally or via SSH and print severity-ranked findings
user-invocable: true
---

# server-audit

Run **`/server-audit`** when you need a fast production triage.

## Usage

```bash
# local machine
bash ~/ai-dotfiles/skills/server-audit/scripts/audit.sh

# remote server
bash ~/ai-dotfiles/skills/server-audit/scripts/audit.sh user@host

# custom SSH port
bash ~/ai-dotfiles/skills/server-audit/scripts/audit.sh user@host 2222
```

## What it checks

1. Docker containers (`docker ps -a`)
2. nginx config (`nginx -T`, first 50 lines)
3. Failed systemd units (`systemctl --failed`)
4. Disk space (`df -h`)
5. Error logs from last hour (`journalctl --since '1 hour ago' -p err`)

## Output contract

- Numbered findings
- Severity prefix: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`
- Ends with a short summary by severity count
