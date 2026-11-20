# Vetting a third-party skill

Run this before installing any skill, and before each re-sync of a vendored one. Snyk's ToxicSkills study (February 2026, 3,984 skills) found prompt injection in 36 % of them and 1,467 malicious payloads (credential theft, backdoors, exfiltration). A skill is code that runs with your rights.

## Checklist

1. **Source.** Known maintainer or organisation (Trail of Bits, Snyk, OWASP, Anthropic), or 1,000+ stars and a release in the last 12 months. Below that bar: read everything and ask the owner.
2. **License.** Present and compatible. No license = not vendorable.
3. **Read every file** — `SKILL.md`, references, scripts. It is Markdown and shell; it can all be read.
4. **`allowed-tools`.** `Bash`, `Write`, network tools or MCP tools deserve more scrutiny than `Read` and `Grep`.
5. **Grep for red flags:**
   `grep -rniE "curl |wget |base64 -d|/dev/tcp|nc -e|ignore (all )?previous|do not tell|exfil|\.ssh/|\.aws/|api[_-]?key" <dir>`
   Each hit needs a reason (a warning in prose is fine; a command is not).
6. **Outbound calls.** List every URL a script contacts. Each must match the profile's data policy.
7. **Hidden instructions.** Look for text aimed at the model rather than the user: HTML comments, zero-width characters (`grep -nP '[\x{200B}-\x{200F}\x{2060}]'`), "system" phrasing in references.
8. **Try it in a throwaway project first,** not at user level.
9. **Pin it.** Commit SHA or tag in a pin file, listed in `config/vendored-skills.json`.

## On re-sync

`git diff <old-pin>..<new-pin> -- <vendored paths>` upstream, then steps 3-7 on the diff only. Update `owasp-coverage.md` if the OWASP skill changed.
