#!/usr/bin/env python3
"""harness-metrics.py: one JSON record per Claude Code session, from its transcript.

  session (--id ID | TRANSCRIPT) [--compact]   print the record (JSON, or one line)
  append TRANSCRIPT --vault PATH [--host NAME] [--reason R]
                                               write or replace the record in
                                               <vault>/meta/harness-sessions/<YYYY-MM>-<host>.jsonl

Stdlib only. The record holds names, counts, durations, cost, ids and repo-relative paths.
It never holds prompts, replies, tool inputs, file contents or hook message text.
"""
import argparse
import glob
import json
import os
import re
import socket
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Refusal prefix (after "PreToolUse:<tool> hook error: ") -> guard name. Only the name is stored.
GUARDS = {
    "local-ci merge guard:": "merge-guard",
    "Commit message format invalid": "commit-scope",
    'Scope "': "commit-scope",
    "hardline-check ": "hardline",
}
HOOK_PREFIX = re.compile(r"^PreToolUse:\S+ hook error: ")
RULE_ID = re.compile(r"\^([a-z]\d+)\b")
EDIT_TOOLS = ("Edit", "Write", "MultiEdit")


def _roots() -> tuple:
    repo = os.environ.get("AI_DOTFILES") or os.path.expanduser("~/ai-dotfiles")
    return repo.rstrip("/") + "/", (os.environ.get("BRAIN_PATH") or "").rstrip("/") + "/"


def harness_path(path: str) -> str | None:
    """Repo-relative path when `path` is a harness file (repo file, vault pitfalls or pattern note)."""
    repo, vault = _roots()
    if path.startswith(repo):
        return path[len(repo):]
    if len(vault) > 1 and path.startswith(vault):
        rel = path[len(vault):]
        if rel.endswith("pitfalls.md") or rel.startswith("resources/knowledge/patterns/"):
            return rel
    return None


def _text(content) -> str:
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content if isinstance(b, dict))
    return content if isinstance(content, str) else ""


def _scan(path: Path, acc: dict, main: bool) -> None:
    """Fold one transcript file into `acc`. Unparseable lines count in acc['bad']."""
    seen = set()  # JSONL writes one line per streamed block: a tool_use id counts once
    with open(path, errors="replace") as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                r = None
            if not isinstance(r, dict):
                acc["bad"] += 1
                continue
            if main:
                acc["records"].append(r)
            t = r.get("type")
            msg = r.get("message") if isinstance(r.get("message"), dict) else {}
            content = msg.get("content")
            if t == "assistant" and isinstance(content, list):
                for x in content:
                    if isinstance(x, dict) and x.get("type") == "tool_use" and x.get("id") not in seen:
                        seen.add(x.get("id"))
                        _tool_use(x, acc, main)
            elif t == "user" and main:
                if isinstance(content, str) or (isinstance(content, list) and any(
                        isinstance(x, dict) and x.get("type") != "tool_result" for x in content)):
                    acc["turns"] += 1
                for x in content if isinstance(content, list) else []:
                    if isinstance(x, dict) and x.get("type") == "tool_result" and x.get("is_error"):
                        _refusal(_text(x.get("content")), acc)


def _tool_use(x: dict, acc: dict, main: bool) -> None:
    name, inp = x.get("name") or "?", x.get("input") or {}
    acc["tools" if main else "sub"][name] += 1
    if main and name == "Skill":
        acc["skills"][inp.get("skill") or "?"] += 1
        if inp.get("skill") == "capture":
            acc["captured"] = True
    elif main and name in ("Agent", "Task"):
        acc["agents"][inp.get("subagent_type") or "general-purpose"] += 1
    elif main and name.startswith("mcp__"):
        acc["mcp"][name.split("__")[1]] += 1
    fp = inp.get("file_path")
    if name in EDIT_TOOLS and isinstance(fp, str):
        if "/inbox/daily/implementation/" in fp:
            acc["captured"] = True
        rel = harness_path(fp)
        if rel:
            acc["edits"].add(rel)
            if name == "Edit" and (rel.endswith("pitfalls.md") or "/patterns/" in "/" + rel):
                old = set(RULE_ID.findall(str(inp.get("old_string") or "")))
                acc["rules"].update(set(RULE_ID.findall(str(inp.get("new_string") or ""))) - old)


def _refusal(text: str, acc: dict) -> None:
    if text.startswith("Permission to use "):
        acc["perm"] += 1
    elif HOOK_PREFIX.match(text):
        body = HOOK_PREFIX.sub("", text, count=1)
        acc["hooks"][next((g for p, g in GUARDS.items() if body.startswith(p)), "other")] += 1


def _ts(s) -> datetime | None:
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def parse_session(transcript: Path) -> dict:
    transcript = Path(transcript)
    acc = {"bad": 0, "records": [], "turns": 0, "skills": Counter(), "agents": Counter(), "mcp": Counter(),
           "tools": Counter(), "sub": Counter(), "hooks": Counter(), "perm": 0, "captured": False,
           "edits": set(), "rules": set()}
    status = "ok"
    try:
        _scan(transcript, acc, True)
        for sub in sorted(glob.glob(str(transcript.with_suffix("") / "subagents" / "*.jsonl"))):
            _scan(Path(sub), acc, False)
    except OSError:
        status = "failed"
    recs = acc["records"]
    if status == "ok" and not recs:
        status = "failed"
    elif acc["bad"]:
        status = "partial"
    cost = next((r for r in reversed(recs) if r.get("type") == "cost-state"), {})
    stamps = [t for t in (_ts(r.get("timestamp")) for r in recs) if t]
    if cost.get("totalDuration") is not None:
        duration = round(cost["totalDuration"] / 1000)
    else:
        duration = round((stamps[-1] - stamps[0]).total_seconds()) if len(stamps) > 1 else 0
    first = recs[0] if recs else {}
    cwd = next((r["cwd"] for r in recs if r.get("cwd")), "")
    return {
        "session_id": first.get("sessionId") or transcript.stem,
        "date": next((r["timestamp"] for r in recs if r.get("timestamp")),
                     datetime.now(timezone.utc).isoformat(timespec="seconds")),
        "project": os.path.basename(cwd.rstrip("/")),
        "host": socket.gethostname(),
        "tool": "claude-code",
        "duration_s": duration,
        "user_turns": acc["turns"],
        "cost_usd": cost.get("totalCostUSD"),
        "tokens": {m: (u.get("inputTokens") or 0) + (u.get("outputTokens") or 0)
                   for m, u in (cost.get("modelUsage") or {}).items()},
        "skills": dict(acc["skills"]),
        "mcp": dict(acc["mcp"]),
        "agents": dict(acc["agents"]),
        "tools": dict(acc["tools"]),
        "subagent_tools": dict(acc["sub"]),
        "hook_refusals": dict(acc["hooks"]),
        "permission_refusals": acc["perm"],
        "captured": acc["captured"],
        "harness_edits": sorted(acc["edits"]),
        "rules_added": sorted(acc["rules"]),
        "reason": None,
        "metrics_status": status,
    }


def append_record(record: dict, vault: Path, host: str) -> Path:
    target = Path(vault) / "meta" / "harness-sessions" / f"{record['date'][:7]}-{host}.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = target.read_text().splitlines() if target.exists() else []
    new = json.dumps(record, ensure_ascii=False)
    for i, line in enumerate(lines):
        try:
            same = json.loads(line).get("session_id") == record["session_id"]
        except (ValueError, AttributeError):
            same = False
        if same:
            lines[i] = new
            break
    else:
        lines.append(new)
    with tempfile.NamedTemporaryFile("w", dir=target.parent, delete=False, suffix=".tmp") as tmp:
        tmp.write("\n".join(lines) + "\n")
    try:
        os.replace(tmp.name, target)
    except BaseException:
        os.unlink(tmp.name)
        raise
    return target


def compact(record: dict) -> str:
    cost = record["cost_usd"]
    return (f"{record['session_id'][:8]} {record['date'][:10]} {record['project']} "
            f"{round(record['duration_s'] / 60)}min {'$%.2f' % cost if cost is not None else '$?'} "
            f"turns={record['user_turns']} skills={sum(record['skills'].values())} "
            f"agents={sum(record['agents'].values())} mcp={sum(record['mcp'].values())} "
            f"refused={sum(record['hook_refusals'].values())}h/{record['permission_refusals']}p "
            f"captured={'yes' if record['captured'] else 'no'} edits={len(record['harness_edits'])} "
            f"rules={len(record['rules_added'])} {record['metrics_status']}")


def _find(session_id: str) -> Path | None:
    root = os.environ.get("CLAUDE_PROJECTS_DIR") or os.path.expanduser("~/.claude/projects")
    hits = glob.glob(os.path.join(root, "*", f"{session_id}.jsonl"))
    return Path(hits[0]) if hits else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("session")
    s.add_argument("transcript", nargs="?")
    s.add_argument("--id")
    s.add_argument("--compact", action="store_true")
    a = sub.add_parser("append")
    a.add_argument("transcript")
    a.add_argument("--vault", required=True)
    a.add_argument("--host", default=socket.gethostname())
    a.add_argument("--reason")
    args = ap.parse_args(argv)
    if args.cmd == "session":
        path = _find(args.id) if args.id else Path(args.transcript) if args.transcript else None
        if path is None:
            print("harness-metrics: transcript not found (give TRANSCRIPT or a known --id)", file=sys.stderr)
            return 2
        rec = parse_session(path)
        print(compact(rec) if args.compact else json.dumps(rec, ensure_ascii=False))
    else:
        rec = parse_session(Path(args.transcript))
        rec["host"], rec["reason"] = args.host, args.reason
        append_record(rec, Path(args.vault), args.host)
    return 0


if __name__ == "__main__":
    sys.exit(main())
