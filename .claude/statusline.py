#!/usr/bin/env python3
"""Custom Claude Code statusline — 3 lines:

  L1  model | project | branch[*]
  L2  ctx N% to compact | K tok
  L3  session N% reset Hh Mm | week N% reset Dd Hh

Reads JSON payload on stdin (as per Claude Code's statusLine hook).
Uses `ccusage blocks --json` and `ccusage daily --json` for session and
weekly usage, cached on disk to keep invocations cheap.

Env overrides:
  COMPACT_PCT             auto-compact threshold (default 95)
  CTX_WINDOW              context window size    (default 200000)
  WEEK_TOKEN_CAP          weekly token cap for % display; 0 = raw count
  CCUSAGE_TOKEN_LIMIT     ccusage --token-limit value (default "max")
  STATUSLINE_CACHE_TTL    seconds for the blocks cache (default 30)
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
WEEK_TOKEN_CAP = int(os.environ.get("WEEK_TOKEN_CAP", "0"))
CCUSAGE_TOKEN_LIMIT = os.environ.get("CCUSAGE_TOKEN_LIMIT", "max")

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


def fmt_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(int(n))


def fmt_hm(seconds: int) -> str:
    if seconds <= 0:
        return "now"
    h, rem = divmod(seconds, 3600)
    m = rem // 60
    return f"{h}h{m:02d}m" if h else f"{m}m"


def fmt_dh(seconds: int) -> str:
    if seconds <= 0:
        return "now"
    d, rem = divmod(seconds, 86400)
    h = rem // 3600
    return f"{d}d{h:02d}h" if d else f"{h}h"


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


def session_info() -> tuple[str, str, int]:
    cmd = ["ccusage", "blocks", "--json"]
    if CCUSAGE_TOKEN_LIMIT:
        cmd += ["--token-limit", CCUSAGE_TOKEN_LIMIT]
    data = cached_json("blocks", cmd, ttl=CACHE_TTL)
    if not data:
        return ("-", "-", 0)
    active = next((b for b in data.get("blocks", []) if b.get("isActive")), None)
    if not active:
        return ("-", "-", 0)
    total = int(active.get("totalTokens") or 0)
    tls = active.get("tokenLimitStatus") or {}
    end = active.get("endTime")
    reset = "-"
    if end:
        dt = _parse_iso(end)
        if dt:
            reset = fmt_hm(int((dt - datetime.now(timezone.utc)).total_seconds()))
    if "percentUsed" in tls:
        pct = int(round(float(tls["percentUsed"])))
        return (f"{pct}%", reset, pct)
    limit = tls.get("limit")
    if limit:
        pct = int(round(total * 100 / int(limit)))
        return (f"{pct}%", reset, pct)
    # no tier/limit known → show raw tokens
    return (fmt_tokens(total), reset, 0)


def week_info() -> tuple[str, str, int]:
    now = datetime.now()
    monday = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    next_monday = monday + timedelta(days=7)
    data = cached_json("daily", ["ccusage", "daily", "--json"], ttl=300)
    total = 0
    if data:
        since = monday.date().isoformat()
        for d in data.get("daily", []):
            date_s = str(d.get("date", ""))
            if date_s < since:
                continue
            t = d.get("totalTokens")
            if t is None:
                t = ((d.get("inputTokens") or 0) + (d.get("outputTokens") or 0)
                     + (d.get("cacheCreationTokens") or 0) + (d.get("cacheReadTokens") or 0))
            total += int(t)
    reset = fmt_dh(int((next_monday - now).total_seconds()))
    if WEEK_TOKEN_CAP > 0:
        pct = int(round(total * 100 / WEEK_TOKEN_CAP))
        return (f"{pct}%", reset, pct)
    return (fmt_tokens(total), reset, 0)


def main() -> int:
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

    l1 = [f"{CYAN}{model}{R}", f"{BOLD}{project}{R}"]
    if branch:
        l1.append(f"{MAGENTA}{branch}{R}")
    line1 = f" {SEP} ".join(l1)

    ctx_tok = last_ctx_tokens(transcript)
    used_pct = int(round(ctx_tok * 100 / CTX_WINDOW)) if CTX_WINDOW else 0
    left_pct = max(0, COMPACT_PCT - used_pct)
    ctx_c = color_for(left_pct, invert=True)
    line2 = (f"{DIM}ctx{R} {ctx_c}{left_pct}%{R} {DIM}to compact{R} {SEP} "
             f"{DIM}{fmt_tokens(ctx_tok)} tok{R}")

    s_str, s_reset, s_pct = session_info()
    w_str, w_reset, w_pct = week_info()
    line3 = (f"{DIM}session{R} {color_for(s_pct)}{s_str}{R} {DIM}reset {s_reset}{R} "
             f"{SEP} "
             f"{DIM}week{R} {color_for(w_pct)}{w_str}{R} {DIM}reset {w_reset}{R}")

    sys.stdout.write(f"{line1}\n{line2}\n{line3}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
