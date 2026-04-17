#!/usr/bin/env python3
"""Custom Claude Code statusline — 3 lines:

  L1  model | project | branch[*]
  L2  ctx N% to compact | K tok
  L3  session N% reset Hh Mm | week N% reset Dd Hh

Reads JSON payload on stdin (as per Claude Code's statusLine hook).
Uses `ccusage blocks --json` and `ccusage daily --json` for session and
weekly usage, cached on disk to keep invocations cheap.

Env overrides:
  COMPACT_PCT                auto-compact threshold (default 95)
  CTX_WINDOW                 context window size    (default 200000)
  CLAUDE_WEEKLY_LIMIT_TOK    weekly baseline for % (default 100000000)
                              Pro-style ~5M/week: set CLAUDE_WEEKLY_LIMIT_TOK=5000000
  CLAUDE_SESSION_LIMIT_TOK   fixed session denominator override (default 0 = auto)
  CCUSAGE_TOKEN_LIMIT        ccusage --token-limit override (default "max")
  STATUSLINE_CACHE_TTL       seconds for the blocks cache (default 30)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "claude-statusline"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CACHE_TTL = int(os.environ.get("STATUSLINE_CACHE_TTL", "30"))
COMPACT_PCT = int(os.environ.get("COMPACT_PCT", "95"))
CTX_WINDOW = int(os.environ.get("CTX_WINDOW", "200000"))
# Weekly baseline for `week N%`: default 100M matches Max / heavy-usage tiers (~7M used → ~7%).
# For Pro-style weekly caps, set CLAUDE_WEEKLY_LIMIT_TOK=5000000 (or your real limit).
WEEKLY_LIMIT_TOK = int(os.environ.get("CLAUDE_WEEKLY_LIMIT_TOK", "100000000"))
SESSION_LIMIT_TOK = int(os.environ.get("CLAUDE_SESSION_LIMIT_TOK", "0"))
CCUSAGE_TOKEN_LIMIT = os.environ.get("CCUSAGE_TOKEN_LIMIT", "max").strip()

R = "\033[0m"
DIM = "\033[2m"; BOLD = "\033[1m"
GREEN = "\033[32m"; YELLOW = "\033[33m"; RED = "\033[31m"
CYAN = "\033[36m"; MAGENTA = "\033[35m"; GRAY = "\033[90m"
SEP = f"{GRAY}|{R}"


def color_for(pct: int, *, invert: bool = False) -> str:
    # invert=True: bigger is better (remaining headroom)
    if invert:
        return GREEN if pct > 30 else YELLOW if pct > 10 else RED
    return GREEN if pct < 60 else YELLOW if pct < 85 else RED


def paint(text: str, color: str, *, enabled: bool) -> str:
    return f"{color}{text}{R}" if enabled else text


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(int(n))


def fmt_cost(cost: float | None) -> str:
    return f"${cost:.3f}" if cost is not None else ""


def fmt_hm(seconds: int) -> str:
    if seconds <= 0:
        return "now"
    h, rem = divmod(seconds, 3600)
    m = rem // 60
    return f"{h}h{m:02d}m" if h else f"{m}m"


def fmt_weekly_reset(target: datetime, now: datetime) -> str:
    seconds = int((target - now).total_seconds())
    if seconds <= 0:
        return "resets now (0 days)"
    days = (seconds + 86399) // 86400
    return f"resets {target.strftime('%a %I:%M %p')} ({days} days)"


def progress_bar(pct: int, width: int = 10) -> str:
    p = max(0, min(100, pct))
    filled = int(round(p * width / 100))
    return f"[{'█' * filled}{'░' * (width - filled)}]"


def should_use_color() -> bool:
    if os.environ.get("FORCE_COLOR"):
        return True
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("CLICOLOR") == "0":
        return False
    return True


def run(cmd: list[str], timeout: float = 3.0) -> str | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def cached_json(key: str, cmd: list[str], ttl: int) -> dict | None:
    f = CACHE_DIR / f"{key}.json"
    if f.exists() and time.time() - f.stat().st_mtime < ttl:
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    out = run(cmd)
    if out:
        try:
            data = json.loads(out)
            f.write_text(out)
            return data
        except Exception:
            pass
    if f.exists():  # stale fallback
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return None


def git_info(cwd: str) -> tuple[str, str]:
    def g(*args: str) -> str | None:
        r = run(["git", "-C", cwd, *args], timeout=1.0)
        return r.strip() if r is not None else None

    top = g("rev-parse", "--show-toplevel")
    project = Path(top).name if top else Path(cwd).name
    branch = g("branch", "--show-current") or g("rev-parse", "--short", "HEAD") or ""
    if branch and g("status", "--porcelain"):
        branch += "*"
    return project, branch


def _find_usage(o):
    if isinstance(o, dict):
        if "input_tokens" in o:
            yield o
        for v in o.values():
            yield from _find_usage(v)
    elif isinstance(o, list):
        for v in o:
            yield from _find_usage(v)


def last_ctx_tokens(transcript: str | None) -> int:
    if not transcript or not os.path.isfile(transcript):
        return 0
    try:
        with open(transcript, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - 200_000))
            blob = fh.read().decode("utf-8", errors="ignore")
    except Exception:
        return 0
    last = None
    for line in blob.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        for u in _find_usage(obj):
            last = u
    if not last:
        return 0
    return (int(last.get("input_tokens") or 0)
            + int(last.get("cache_creation_input_tokens") or 0)
            + int(last.get("cache_read_input_tokens") or 0))


def _parse_iso(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def session_info() -> tuple[str, str, int, float | None, dict]:
    cmd = ["ccusage", "blocks", "--json"]
    if CCUSAGE_TOKEN_LIMIT:
        cmd += ["--token-limit", CCUSAGE_TOKEN_LIMIT]
    data = cached_json("blocks", cmd, ttl=CACHE_TTL)
    if not data:
        return ("-", "-", 0, None, {"source": "none"})
    active = next((b for b in data.get("blocks", []) if b.get("isActive")), None)
    if not active:
        return ("-", "-", 0, None, {"source": "none"})
    total = int(active.get("totalTokens") or 0)
    tls = active.get("tokenLimitStatus") or {}
    end = active.get("endTime")
    reset = "-"
    if end:
        dt = _parse_iso(end)
        if dt:
            reset = fmt_hm(int((dt - datetime.now(timezone.utc)).total_seconds()))
    limit = tls.get("limit")
    # Prefer explicit user override for deterministic % (useful for Pro plan tuning).
    if SESSION_LIMIT_TOK > 0:
        limit = SESSION_LIMIT_TOK
    if limit:
        # ccusage tokenLimitStatus.percentUsed is projected usage (% at end of block),
        # not current usage. For statusline "session %", use current total/limit.
        limit_i = int(limit)
        pct_float = (total * 100.0 / limit_i) if limit_i > 0 else 0.0
        pct = int(round(pct_float))
        return (
            f"{pct}%",
            reset,
            pct,
            float(active.get("costUSD")) if active.get("costUSD") is not None else None,
            {
                "source": "current_total_over_limit",
                "totalTokens": total,
                "limit": limit_i,
                "limitFromOverride": SESSION_LIMIT_TOK > 0,
                "projectedPercentUsed": tls.get("percentUsed"),
                "projectedUsage": tls.get("projectedUsage"),
                "computed": {
                    "formula": "round(totalTokens * 100 / limit)",
                    "percentRaw": round(pct_float, 6),
                    "percentRounded": pct,
                    "remainingTokens": max(0, limit_i - total),
                },
            },
        )
    if "percentUsed" in tls:
        pct = int(round(float(tls["percentUsed"])))
        return (
            f"{pct}%",
            reset,
            pct,
            float(active.get("costUSD")) if active.get("costUSD") is not None else None,
            {
                "source": "projected_percent_used_fallback",
                "totalTokens": total,
                "limit": tls.get("limit"),
                "projectedPercentUsed": tls.get("percentUsed"),
                "projectedUsage": tls.get("projectedUsage"),
                "computed": {
                    "formula": "round(projectedPercentUsed)",
                    "percentRaw": float(tls.get("percentUsed")),
                    "percentRounded": pct,
                },
            },
        )
    # no tier/limit known → show raw tokens
    return (
        fmt_tokens(total),
        reset,
        0,
        float(active.get("costUSD")) if active.get("costUSD") is not None else None,
        {
            "source": "raw_tokens_only",
            "totalTokens": total,
            "limit": None,
            "computed": {"formula": "no limit available; display raw tokens"},
        },
    )


def week_info() -> tuple[int, str, dict]:
    now = datetime.now()
    # Weekly reset label target in local time: Friday 10:00 AM.
    reset = now.replace(hour=10, minute=0, second=0, microsecond=0)
    days_until_friday = (4 - now.weekday()) % 7
    reset = reset + timedelta(days=days_until_friday)
    if reset <= now:
        reset = reset + timedelta(days=7)
    data = cached_json("daily", ["ccusage", "daily", "--json"], ttl=300)
    total = 0
    if data:
        since = (reset - timedelta(days=7)).date().isoformat()
        for d in data.get("daily", []):
            date_s = str(d.get("date", ""))
            if date_s < since:
                continue
            t = d.get("totalTokens")
            if t is None:
                t = ((d.get("inputTokens") or 0) + (d.get("outputTokens") or 0)
                     + (d.get("cacheCreationTokens") or 0) + (d.get("cacheReadTokens") or 0))
            total += int(t)
    pct_float = (total * 100.0 / WEEKLY_LIMIT_TOK) if WEEKLY_LIMIT_TOK > 0 else 0.0
    pct = int(round(pct_float)) if WEEKLY_LIMIT_TOK > 0 else 0
    return (
        pct,
        fmt_weekly_reset(reset, now),
        {
            "source": "rolling_window_sum_over_weekly_limit",
            "windowStart": since,
            "windowEnd": reset.date().isoformat(),
            "weeklyTotalTokens": total,
            "weeklyLimitTokens": WEEKLY_LIMIT_TOK,
            "computed": {
                "formula": "round(weeklyTotalTokens * 100 / weeklyLimitTokens)",
                "percentRaw": round(pct_float, 6),
                "percentRounded": pct,
                "remainingTokens": max(0, WEEKLY_LIMIT_TOK - total),
            },
        },
    )


def main() -> int:
    debug_mode = "--debug" in sys.argv[1:]
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        payload = {}

    model_obj = payload.get("model") or {}
    model = model_obj.get("display_name") or model_obj.get("id") or "claude"
    param = model_obj.get("param_summary")
    if param:
        model = f"{model} {param}"

    ws = payload.get("workspace") or {}
    cwd = ws.get("current_dir") or payload.get("cwd") or os.getcwd()
    transcript = payload.get("transcript_path")

    project, branch = git_info(cwd)

    ansi = should_use_color()
    sep = SEP if ansi else "|"
    l1 = [paint(model, CYAN, enabled=ansi), paint(project, BOLD, enabled=ansi)]
    if branch:
        l1.append(paint(branch, MAGENTA, enabled=ansi))
    line1 = f" {sep} ".join(l1)

    ctx_tok = last_ctx_tokens(transcript)
    compact_window = int(CTX_WINDOW * (COMPACT_PCT / 100.0)) if CTX_WINDOW and COMPACT_PCT else 0
    used_pct = int(round(ctx_tok * 100 / compact_window)) if compact_window else 0
    used_pct = max(0, min(100, used_pct))
    # ctx % semantics:
    # - ctx % = how far into this session's compaction window has been consumed.
    # - depends on COMPACT_PCT (or CLAUDE_AUTOCOMPACT_PCT_OVERRIDE) and effective context size.
    # - different sessions can show different % with different absolute tokens; this is expected.
    bar = progress_bar(used_pct, width=10)
    bar_c = color_for(used_pct)
    cost = None
    p_cost = (payload.get("cost") or {}).get("total_cost_usd")
    if p_cost is not None:
        try:
            cost = float(p_cost)
        except Exception:
            cost = None
    line2_parts = [
        f"{paint('ctx', DIM, enabled=ansi)} {paint(bar, bar_c, enabled=ansi)} {paint(f'{used_pct}%', bar_c, enabled=ansi)}",
        f"{paint(f'{fmt_tokens(ctx_tok)} tok used', DIM, enabled=ansi)}",
    ]
    if cost is not None:
        line2_parts.append(paint(fmt_cost(cost), DIM, enabled=ansi))
    line2 = f" {sep} ".join(line2_parts)

    s_str, s_reset, s_pct, s_cost, s_dbg = session_info()
    if cost is None:
        cost = s_cost
        if cost is not None:
            line2 += f" {sep} {paint(fmt_cost(cost), DIM, enabled=ansi)}"

    w_pct, w_reset, w_dbg = week_info()
    line3 = (f"{paint('session', DIM, enabled=ansi)} {paint(s_str, color_for(s_pct), enabled=ansi)} "
             f"{paint(f'reset {s_reset}', DIM, enabled=ansi)} "
             f"{sep} "
             f"{paint('week', DIM, enabled=ansi)} {paint(f'{w_pct}%', color_for(w_pct), enabled=ansi)} "
             f"{paint(w_reset, DIM, enabled=ansi)}")

    if debug_mode:
        debug_payload = {
            "session": s_dbg,
            "week": w_dbg,
            "config": {
                "COMPACT_PCT": COMPACT_PCT,
                "CTX_WINDOW": CTX_WINDOW,
                "CLAUDE_WEEKLY_LIMIT_TOK": WEEKLY_LIMIT_TOK,
                "CLAUDE_SESSION_LIMIT_TOK": SESSION_LIMIT_TOK,
                "CCUSAGE_TOKEN_LIMIT": CCUSAGE_TOKEN_LIMIT or None,
            },
        }
        sys.stdout.write(json.dumps(debug_payload, indent=2))
        return 0

    sys.stdout.write(f"{line1}\n{line2}\n{line3}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
