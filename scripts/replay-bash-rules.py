#!/usr/bin/env python3
"""Replay past Claude Code Bash calls through hardline-check.py and the template permissions.ask list.

Usage: replay-bash-rules.py [--days N]   (default 14; read-only)
- Input: main transcripts ~/.claude/projects/*/*.jsonl. Subagent transcripts
  ~/.claude/projects/*/<session>/subagents/*.jsonl are counted in a separate column.
- Dedupe: by tool_use.id (one call can span several JSONL lines). Lines without a tool_use block are ignored.
- Active day: a UTC date with >= 1 Bash tool_use in a main transcript.
- Prompt: an "ask" from the hook's classify(), or else a template Bash(...) ask rule that matches a simple
  command (approximation of Claude Code's own matcher). Denies are counted apart: they never prompt.
- Output: prompts per rule, per session and per day, then every prompt and deny with an empty label column.
"""
import argparse, collections, datetime as dt, fnmatch, importlib.util, json  # noqa: E401
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("hardline", ROOT / ".claude/hooks/hardline-check.py")
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)
ASK = [r[5:-1] for r in json.loads((ROOT / ".claude/settings.json.tpl").read_text())["permissions"].get("ask", [])
       if r.startswith("Bash(")]


def settings_ask(cmd):
    stripped, bodies = hook.strip_heredocs(cmd)
    try:
        cmds = hook.commands(stripped)
    except ValueError:
        return None
    for c in cmds:
        prog, args, _ = hook.resolve(c, bodies)
        text = " ".join([prog] + args)
        for pat in ASK:
            if fnmatch.fnmatchcase(text, pat) or text == pat.removesuffix(" *"):
                return ("ask", f"settings:{pat}", "")
    return None


def calls(days):
    since, seen = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days), {}
    base = Path.home() / ".claude" / "projects"
    for src, pattern in (("main", "*/*.jsonl"), ("subagent", "*/*/subagents/*.jsonl")):
        for f in sorted(base.glob(pattern)):
            session = f.stem if src == "main" else f.parent.parent.name
            for raw in f.open(errors="replace"):
                if '"tool_use"' not in raw:
                    continue
                try:
                    d = json.loads(raw)
                    ts = dt.datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00"))
                except (ValueError, KeyError, AttributeError):
                    continue
                content = (d.get("message") or {}).get("content")
                for b in content if isinstance(content, list) and ts >= since else []:
                    if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Bash":
                        cmd = (b.get("input") or {}).get("command") or ""
                        seen.setdefault(b.get("id"), (src, session, ts.date().isoformat(), cmd))
    return seen.values()


def table(title, rows):
    print(f"\n### {title}\n\n| {title.split()[-1]} | main | subagent |\n|---|---|---|")
    for key in sorted({k for k, _ in rows}):
        print(f"| {key} | {rows[key, 'main']} | {rows[key, 'subagent']} |")


def main():
    ap =argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=14)
    days = ap.parse_args().days
    n, sessions, active, listed = collections.Counter(), collections.defaultdict(set), set(), []
    per = {k: collections.Counter() for k in ("rule", "session", "day")}
    for src, session, day, cmd in calls(days):
        n["Bash calls", src] += 1
        sessions[src].add(session)
        active.add(day) if src == "main" else None
        hit = hook.classify(cmd) or settings_ask(cmd)
        if not hit:
            continue
        n["Prompts" if hit[0] == "ask" else "Denies", src] += 1
        if hit[0] == "ask":
            for k, v in (("rule", hit[1]), ("session", session), ("day", day)):
                per[k][v, src] += 1
        listed.append((day, src, session, hit[0], hit[1], cmd))
    print(__doc__.split("\n\n", 1)[1].split("- Output")[0].rstrip())
    print(f"\nWindow: last {days} days (UTC).\n\n| | main | subagent |\n|---|---|---|")
    for key in ("Bash calls", "Prompts", "Denies"):
        print(f"| {key} | {n[key, 'main']} | {n[key, 'subagent']} |")
    print(f"| Sessions | {len(sessions['main'])} | {len(sessions['subagent'])} |\n| Active days | {len(active)} | - |")
    rate = (n["Prompts", "main"] + n["Prompts", "subagent"]) / len(active) if active else 0
    print(f"\nPrompts per active day (all sources): {rate:.2f}")
    for title, key in (("Prompts per rule", "rule"), ("Prompts per session", "session"), ("Prompts per day", "day")):
        table(title, per[key])
    print("\n### Every prompt and deny\n\n| date | source | session | decision | rule | command | label |")
    print("|---|---|---|---|---|---|---|")
    for day, src, session, dec, rule, cmd in sorted(listed):
        text = cmd[:200].replace("\n", " ⏎ ").replace("|", "\\|")
        print(f"| {day} | {src} | {session} | {dec} | {rule} | {text} |  |")


if __name__ == "__main__":
    main()
