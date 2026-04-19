#!/usr/bin/env python3
"""Custom Claude Code statusline — 3 lines:

  L1  model | project | branch[*]
  L2  ctx N% to compact | K tok
  L3  session N% reset Hh Mm | week N% reset Dd Hh

Reads JSON payload on stdin (as per Claude Code's statusLine hook).
Session % / reset and weekly token totals walk transcript JSONL files under
~/.claude/projects (no network). Assistant rows with the same API message id
(streaming chunks) are counted once per id so totals match real usage.

Calibrate the denominators to what Claude Code itself shows in /status:
  - Block-total / session% = your real 5h limit  (set CLAUDE_SESSION_LIMIT_TOK)
  - Week-total / week%     = your real 7d limit  (set CLAUDE_WEEKLY_LIMIT_TOK)
The numerators are measured from transcripts; only denominators are tunable.

Env overrides:
  COMPACT_PCT                auto-compact threshold (default 95)
  CTX_WINDOW                 context window size    (default 200000)
  CLAUDE_SESSION_LIMIT_TOK   session (5h block) denominator (default 17000000)
  CLAUDE_WEEKLY_LIMIT_TOK    weekly (7d) denominator (default 500000000)
  STATUSLINE_CACHE_TTL       seconds for the disk cache (default 30)
  STATUSLINE_SESSION_TAIL_BYTES  bytes read from end of each transcript (default 2000000)
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

def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


CACHE_TTL = _int_env("STATUSLINE_CACHE_TTL", 30)
COMPACT_PCT = _int_env("COMPACT_PCT", 95)
CTX_WINDOW = _int_env("CTX_WINDOW", 200000)
WEEKLY_LIMIT_TOK = _int_env("CLAUDE_WEEKLY_LIMIT_TOK", 580_000_000)
SESSION_LIMIT_TOK = _int_env("CLAUDE_SESSION_LIMIT_TOK", 19_000_000)
# Weekly reset: 0=Mon .. 6=Sun; hour is local 24h. Default Fri 10:00.
WEEKLY_RESET_DAY = _int_env("CLAUDE_WEEKLY_RESET_DAY", 4)
WEEKLY_RESET_HOUR = _int_env("CLAUDE_WEEKLY_RESET_HOUR", 10)
STATUSLINE_DEBUG = os.environ.get("STATUSLINE_DEBUG") == "1"

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
    # %-I drops leading zero on Linux/macOS; fall back to %I if unsupported.
    try:
        ts = target.strftime("%a %-I:%M %p")
    except ValueError:
        ts = target.strftime("%a %I:%M %p")
    return f"resets {ts} ({days} days)"


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


def _git_run(cwd: str, *args: str, timeout: float = 1.0) -> str | None:
    try:
        r = subprocess.run(["git", "-C", cwd, *args], capture_output=True,
                           text=True, timeout=timeout, check=False)
        return r.stdout if r.returncode == 0 else None
    except Exception as exc:
        if STATUSLINE_DEBUG:
            sys.stderr.write(f"[statusline] git {args[0] if args else ''} raised: {exc}\n")
        return None


def git_info(cwd: str) -> tuple[str, str]:
    def g(*args: str) -> str | None:
        r = _git_run(cwd, *args)
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
        except json.JSONDecodeError:
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
    except (ValueError, TypeError, OSError):
        return None


SESSION_BLOCK = timedelta(hours=5)
TRANSCRIPTS_ROOT = Path.home() / ".claude" / "projects"
SESSION_TAIL_BYTES = _int_env("STATUSLINE_SESSION_TAIL_BYTES", 2_000_000)


def _iter_assistant_usage(path: Path, since: datetime):
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - SESSION_TAIL_BYTES))
            blob = fh.read().decode("utf-8", errors="ignore")
    except OSError:
        return
    pending: list[tuple[datetime, int, str | None]] = []
    for line in blob.splitlines():
        line = line.strip()
        if not line or '"usage"' not in line or '"assistant"' not in line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") != "assistant":
            continue
        ts = _parse_iso(obj.get("timestamp") or "")
        if ts is None or ts < since:
            continue
        msg = obj.get("message") or {}
        usage = msg.get("usage") or {}
        tokens = (int(usage.get("input_tokens") or 0)
                  + int(usage.get("output_tokens") or 0)
                  + int(usage.get("cache_creation_input_tokens") or 0)
                  + int(usage.get("cache_read_input_tokens") or 0))
        if tokens <= 0:
            continue
        mid = msg.get("id")
        pending.append((ts, tokens, str(mid) if mid else None))

    if not pending:
        return
    last_idx: dict[str, int] = {}
    for i, (_, _, mid) in enumerate(pending):
        if mid:
            last_idx[mid] = i
    for i, (ts, tokens, mid) in enumerate(pending):
        if mid and last_idx.get(mid) != i:
            continue
        yield ts, tokens


def _collect_recent_usage(lookback: datetime) -> list[tuple[datetime, int]]:
    if not TRANSCRIPTS_ROOT.is_dir():
        return []
    mtime_cutoff = lookback.timestamp()
    entries: list[tuple[datetime, int]] = []
    for path in TRANSCRIPTS_ROOT.rglob("*.jsonl"):
        try:
            if path.stat().st_mtime < mtime_cutoff:
                continue
        except OSError:
            continue
        entries.extend(_iter_assistant_usage(path, lookback))
    entries.sort(key=lambda p: p[0])
    return entries


def _active_block_start(entries: list[tuple[datetime, int]]) -> datetime:
    # A block is a fixed 5h wall clock from its first message. Walk forward;
    # whenever a message lands after (start + 5h) it opens a new block,
    # regardless of whether there was a gap in activity.
    start = entries[0][0]
    for ts, _ in entries[1:]:
        if ts > start + SESSION_BLOCK:
            start = ts
    return start


def session_info() -> tuple[str, str, int, float | None, dict]:
    now = datetime.now(timezone.utc)
    # 10h lookback: enough to detect a block start that's up to 5h old while
    # tolerating a few hours of prior inactivity. Bounded to keep disk scan cheap.
    lookback = now - timedelta(hours=10)
    entries = _collect_recent_usage(lookback)
    if not entries:
        return ("-", "-", 0, None, {"source": "transcripts_empty"})

    block_start = _active_block_start(entries)
    block_end = block_start + SESSION_BLOCK
    in_block = [(ts, tok) for ts, tok in entries if block_start <= ts <= block_end]
    total = sum(tok for _, tok in in_block)

    reset_sec = int((block_end - now).total_seconds())
    reset = fmt_hm(reset_sec) if reset_sec > 0 else "now"

    dbg: dict = {
        "source": "transcripts_direct",
        "blockStart": block_start.isoformat(),
        "blockEnd": block_end.isoformat(),
        "messageCount": len(in_block),
        "totalTokens": total,
        "limit": SESSION_LIMIT_TOK or None,
    }
    limit = SESSION_LIMIT_TOK if SESSION_LIMIT_TOK > 0 else 1
    pct_float = total * 100.0 / limit
    pct = int(round(pct_float))
    dbg["computed"] = {
        "formula": "round(totalTokens * 100 / SESSION_LIMIT_TOK)",
        "percentRaw": round(pct_float, 6),
        "percentRounded": pct,
        "remainingTokens": max(0, limit - total),
    }
    return (f"{pct}%", reset, pct, None, dbg)


WEEK_CACHE = CACHE_DIR / "week_sum.json"
WEEK_CACHE_TTL = 300


def _week_total_from_transcripts(since: datetime) -> int:
    cached = None
    if WEEK_CACHE.exists() and time.time() - WEEK_CACHE.stat().st_mtime < WEEK_CACHE_TTL:
        try:
            cached = json.loads(WEEK_CACHE.read_text())
        except Exception:
            cached = None
    if cached and cached.get("since") == since.isoformat():
        return int(cached.get("total") or 0)
    if not TRANSCRIPTS_ROOT.is_dir():
        return 0
    mtime_cutoff = since.timestamp()
    total = 0
    for path in TRANSCRIPTS_ROOT.rglob("*.jsonl"):
        try:
            if path.stat().st_mtime < mtime_cutoff:
                continue
        except OSError:
            continue
        for _ts, tok in _iter_assistant_usage(path, since):
            total += tok
    try:
        WEEK_CACHE.write_text(json.dumps({"since": since.isoformat(), "total": total}))
    except OSError:
        pass
    return total


def week_info() -> tuple[int, str, dict]:
    now = datetime.now()
    # Anthropic's weekly limit is tied to an account anchor we don't know; best
    # proxy is a rolling 7-day window ending now. Reset display uses the
    # configured anchor (CLAUDE_WEEKLY_RESET_DAY / _HOUR) for a human ETA.
    reset = now.replace(hour=WEEKLY_RESET_HOUR, minute=0, second=0, microsecond=0)
    days_until = (WEEKLY_RESET_DAY - now.weekday()) % 7
    reset = reset + timedelta(days=days_until)
    if reset <= now:
        reset = reset + timedelta(days=7)
    since_dt = datetime.now(timezone.utc) - timedelta(days=7)
    total = _week_total_from_transcripts(since_dt)
    pct_float = (total * 100.0 / WEEKLY_LIMIT_TOK) if WEEKLY_LIMIT_TOK > 0 else 0.0
    pct = int(round(pct_float)) if WEEKLY_LIMIT_TOK > 0 else 0
    return (
        pct,
        fmt_weekly_reset(reset, now),
        {
            "source": "transcripts_direct",
            "windowStart": since_dt.isoformat(),
            "windowEnd": reset.astimezone(timezone.utc).isoformat(),
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
            },
            "rendered": [line1, line2, line3],
        }
        sys.stdout.write(json.dumps(debug_payload, indent=2))
        return 0

    sys.stdout.write(f"{line1}\n{line2}\n{line3}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
