#!/usr/bin/env python3
"""Replay past Claude Code turns through the prose-question rule of bin/aif-agent-hook.

Usage: replay-prose-questions.py [--days N]   (default 30; read-only)
- Input: main transcripts ~/.claude/projects/*/*.jsonl (sidechain records are ignored).
- Turn: the assistant records between two user prompts (a tool_result is not a prompt).
  Its last assistant text is what the Stop hook receives as last_assistant_message.
- Rule (same as the Stop branch of bin/aif-agent-hook): the last non-empty line ends with ? or ？,
  does not start with ``` and is not a URL holding a "?".
- Active day: a UTC date with >= 1 turn.
- Output: matches, turns, active_days, matches_per_active_day, then 20 sampled last lines.
  Only the last line of a message is printed, never more.
"""
import argparse, datetime as dt, json, random, re  # noqa: E401
from pathlib import Path


def is_question(message):
    """Mirror of the jq rule in bin/aif-agent-hook (Stop)."""
    lines = re.sub(r"\s+$", "", message).split("\n")
    last = lines[-1] if lines else ""
    return (last.endswith(("?", "？")) and not re.match(r"\s*```", last)
            and not re.search(r"https?://\S*\?\S*$", last))


def last_line(message):
    return re.sub(r"\s+$", "", message).split("\n")[-1]


def turns(days):
    since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    for f in sorted((Path.home() / ".claude" / "projects").glob("*/*.jsonl")):
        text, day = None, None
        for raw in f.open(errors="replace"):
            if '"type":"assistant"' not in raw and '"type":"user"' not in raw:
                continue
            try:
                d = json.loads(raw)
                ts = dt.datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00"))
            except (ValueError, KeyError, AttributeError):
                continue
            if d.get("isSidechain") or ts < since:
                continue
            content = (d.get("message") or {}).get("content")
            if d.get("type") == "assistant":
                blocks = content if isinstance(content, list) else []
                text = "\n".join(b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text")
                day = ts.date().isoformat()
            elif not (isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content)):
                if day:
                    yield day, text
                text, day = None, None
        if day:
            yield day, text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    args = ap.parse_args()
    n, active, hits = 0, set(), []
    for day, text in turns(args.days):
        n += 1
        active.add(day)
        if text and is_question(text):
            hits.append(last_line(text)[:200])
    per_day = len(hits) / len(active) if active else 0
    print(f"matches={len(hits)} turns={n} active_days={len(active)} matches_per_active_day={per_day:.1f}")
    for line in random.Random(0).sample(hits, min(20, len(hits))):
        print("-", line)


if __name__ == "__main__":
    main()
