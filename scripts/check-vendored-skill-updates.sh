#!/usr/bin/env bash
# Compare vendored skill pins to GitHub latest releases (cached, fail-open).
# Usage: check-vendored-skill-updates.sh [--inject]
#   --inject  print a short WARNING block for SessionStart context (only if behind)
# Exit 0 always (fail-open). Behind lines also go to the log file.
set -u

AI_DOTFILES="${AI_DOTFILES:-$HOME/ai-dotfiles}"
CFG="${VENDORED_SKILLS_CFG:-$AI_DOTFILES/config/vendored-skills.json}"
CACHE_DIR="${VENDORED_SKILLS_CACHE_DIR:-$HOME/.claude/cache}"
CACHE_FILE="${VENDORED_SKILLS_CACHE:-$CACHE_DIR/vendored-skill-updates.json}"
LOG_FILE="${VENDORED_SKILLS_LOG:-$AI_DOTFILES/.claude/logs/vendored-skill-updates.log}"
CURL_MAX="${VENDORED_SKILLS_CURL_MAX:-3}"
RETRY_SEC="${VENDORED_SKILLS_RETRY_SEC:-900}"

INJECT=0
[[ "${1:-}" == "--inject" ]] && INJECT=1

mkdir -p "$CACHE_DIR" "$(dirname "$LOG_FILE")" 2>/dev/null || true

log() {
  printf '%s %s\n' "$(date -Iseconds 2>/dev/null || date)" "$*" >>"$LOG_FILE" 2>/dev/null || true
}

# Always exit 0 for hooks
trap 'exit 0' EXIT

if [[ ! -f "$CFG" ]]; then
  log "SKIP no config $CFG"
  exit 0
fi

if ! command -v python3 >/dev/null 2>&1; then
  log "SKIP no python3"
  exit 0
fi

OUT=$(
  CURL_MAX="$CURL_MAX" RETRY_SEC="$RETRY_SEC" AI_DOTFILES="$AI_DOTFILES" \
  CACHE_FILE="$CACHE_FILE" CFG="$CFG" LOG_FILE="$LOG_FILE" python3 - <<'PY' 2>/dev/null || true
import json, os, ssl, urllib.request, time, re, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

cfg_path = Path(os.environ["CFG"])
cache_path = Path(os.environ["CACHE_FILE"])
log_path = Path(os.environ["LOG_FILE"])
root = Path(os.environ["AI_DOTFILES"])
curl_max = float(os.environ.get("CURL_MAX", "3"))
retry_sec = float(os.environ.get("RETRY_SEC", "900"))

try:
    cfg = json.loads(cfg_path.read_text())
except Exception as e:
    sys.stderr.write("SKIP bad config: %s\n" % e)
    sys.exit(0)

interval_h = float(cfg.get("check_interval_hours", 24))
interval_s = max(3600.0, interval_h * 3600.0)
now = time.time()

cache = {"checked_at": 0, "skills": {}}
if cache_path.exists():
    try:
        cache = json.loads(cache_path.read_text())
    except Exception:
        pass

skills_out = dict(cache.get("skills") or {})
stale = (now - float(cache.get("checked_at") or 0)) >= interval_s


def norm(tag):
    t = (tag or "").strip()
    if t[:1] in ("v", "V"):
        t = t[1:]
    return t


def fetch_latest(repo):
    url = "https://api.github.com/repos/%s/releases/latest" % repo
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "ai-dotfiles-vendored-check",
        },
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=curl_max, context=ctx) as resp:
            data = json.loads(resp.read().decode())
        return data.get("tag_name")
    except Exception:
        return None


def compare_status(pin, latest):
    """Return ok | behind | ahead | unknown."""
    if not pin or not latest:
        return "unknown"
    np, nl = norm(pin), norm(latest)
    if np == nl:
        return "ok"
    try:
        def parts(s):
            out = []
            for x in re.split(r"[.\-+]", s):
                if x.isdigit():
                    out.append(int(x))
                elif x:
                    out.append(x)
            return out

        a, b = parts(np), parts(nl)
        # Only compare when both are int-leading semver-ish
        if a and b and isinstance(a[0], int) and isinstance(b[0], int):
            if a < b:
                return "behind"
            if a > b:
                return "ahead"
            return "ok"
    except Exception:
        pass
    # Non-comparable unequal tags: unknown (no false WARNING)
    return "unknown"


entries = list(cfg.get("skills") or [])
any_fetch_failed = False

if stale:
    # Parallel GitHub fetches (shared wall-clock ~curl_max, not N * curl_max)
    to_fetch = []
    for entry in entries:
        name = entry.get("name") or ""
        pin_rel = entry.get("pin_file") or ""
        repo = entry.get("github") or ""
        if not name or not pin_rel or not repo:
            continue
        pin_path = root / pin_rel
        if not pin_path.is_file():
            skills_out[name] = {
                "pin": None,
                "latest": (skills_out.get(name) or {}).get("latest"),
                "status": "missing_pin",
                "github": repo,
            }
            continue
        pin = pin_path.read_text().strip().splitlines()[0].strip()
        to_fetch.append((name, pin, repo))

    results = {}
    if to_fetch:
        with ThreadPoolExecutor(max_workers=max(1, len(to_fetch))) as pool:
            futs = {pool.submit(fetch_latest, repo): (name, pin, repo) for name, pin, repo in to_fetch}
            for fut in as_completed(futs):
                name, pin, repo = futs[fut]
                try:
                    latest = fut.result()
                except Exception:
                    latest = None
                results[name] = (pin, repo, latest)

    for name, pin, repo in to_fetch:
        pin, repo, latest = results.get(name, (pin, repo, None))
        prev = skills_out.get(name) or {}
        if latest is None:
            any_fetch_failed = True
            skills_out[name] = {
                "pin": pin,
                "latest": prev.get("latest"),
                "status": "fetch_failed",
                "github": repo,
            }
            continue
        skills_out[name] = {
            "pin": pin,
            "latest": latest,
            "status": compare_status(pin, latest),
            "github": repo,
        }

    if any_fetch_failed:
        # Retry soon — do not freeze a failed refresh for a full day
        prev_checked = float(cache.get("checked_at") or 0)
        if prev_checked <= 0:
            cache["checked_at"] = now - interval_s + retry_sec
        else:
            # keep stale enough that next session retries after retry_sec from now
            cache["checked_at"] = now - interval_s + retry_sec
    else:
        cache["checked_at"] = now
else:
    # Fresh cache: re-read pins from disk and recompute status (no network)
    for entry in entries:
        name = entry.get("name") or ""
        pin_rel = entry.get("pin_file") or ""
        if not name or name not in skills_out:
            continue
        pin_path = root / pin_rel
        info = skills_out[name]
        if not pin_path.is_file():
            info["pin"] = None
            info["status"] = "missing_pin"
            continue
        pin = pin_path.read_text().strip().splitlines()[0].strip()
        info["pin"] = pin
        latest = info.get("latest") or ""
        if not latest:
            if info.get("status") != "fetch_failed":
                info["status"] = "unknown"
        else:
            info["status"] = compare_status(pin, latest)
        skills_out[name] = info

cache["skills"] = skills_out

# Persist (including recomputed pin/status on fresh path) so log matches inject
try:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=2) + "\n")
except Exception:
    pass

# Log from final skills_out
try:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    if ts and len(ts) >= 5 and (ts[-5] in "+-" and ts[-3] != ":"):
        ts = ts[:-2] + ":" + ts[-2:]
    lines = []
    for name, info in sorted(skills_out.items()):
        lines.append(
            "%s %s status=%s pin=%s latest=%s"
            % (ts, name, info.get("status"), info.get("pin"), info.get("latest"))
        )
    if lines:
        with log_path.open("a") as f:
            f.write("\n".join(lines) + "\n")
except Exception:
    pass

behind = []
for name, info in sorted(skills_out.items()):
    if info.get("status") == "behind" and info.get("pin") and info.get("latest"):
        behind.append(
            "%s pinned %s; upstream %s (https://github.com/%s/releases)"
            % (name, info["pin"], info["latest"], info.get("github") or "")
        )

if behind:
    print("--- VENDORED SKILL UPDATES ---")
    for line in behind:
        print("WARNING: %s" % line)
    print("Re-sync: diff pin→tag, replace skills/<name>/, bump pin file, CHANGELOG, install.sh.")
    print("--- END VENDORED SKILL UPDATES ---")
PY
)

if [[ "$INJECT" -eq 1 && -n "${OUT:-}" ]]; then
  printf '%s\n' "$OUT"
fi

exit 0
