#!/usr/bin/env python3
"""harness-metrics.py: one JSON record per Claude Code session, from its transcript.

  session (--id ID | TRANSCRIPT) [--compact]   print the record (JSON, or one line)
  append TRANSCRIPT --vault PATH [--host NAME] [--reason R]
                                               write or replace the record in
                                               <vault>/meta/harness-sessions/<YYYY-MM>-<host>.jsonl
  history --vault PATH [--projects DIR] [--skill-log FILE]
                                               one JSON aggregate over all transcripts, the skill log and the vault
  changes --vault PATH [--days 7]              JSON list of /capture harness-change rows older than --days with no verdict, and of malformed rows

Stdlib only. The record holds names, counts, durations, cost, ids and repo-relative paths.
It never holds prompts, replies, tool inputs, file contents or hook message text.
"""
import argparse
import glob
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone
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
RULE_DEF = re.compile(r"\^([a-z]\d+)\s*$")  # a definition ends its line; references do not
RETIRED = re.compile(r"\^[a-z]\d+\s*→\s*\^[a-z]\d+")  # `^v2→^v1` retired-id mapping, not a definition
EDIT_TOOLS = ("Edit", "Write", "MultiEdit")
REPO_DIR = Path(__file__).resolve().parents[1]
RULE_FILES = ("resources/operational/ai-agents/pitfalls.md", "resources/knowledge/patterns")
HOOK_CONFIGS = (".claude/settings.json.tpl", ".cursor/hooks.json", ".vibe/user-hooks.toml")
HOOK_COMMAND = re.compile(r'^\s*"?command"?\s*[:=]')


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


def _rule_defs(text) -> set:
    lines = str(text or "").splitlines()
    return {m[1] for ln in lines if not RETIRED.search(ln) and (m := RULE_DEF.search(ln))}


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
                acc["rules"].update(_rule_defs(inp.get("new_string")) - _rule_defs(inp.get("old_string")))


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
    tmp = tempfile.NamedTemporaryFile("w", dir=target.parent, delete=False, suffix=".tmp")
    try:
        with tmp:  # closed before the rename: NTFS (drvfs) cannot rename or unlink an open file
            tmp.write("\n".join(lines) + "\n")
        os.replace(tmp.name, target)
    except BaseException:
        Path(tmp.name).unlink(missing_ok=True)
        raise
    return target


def _leaf(value, label: str, source: str) -> dict:
    return {"value": value, "label": label, "source": source}


def _tally(records: list, key: str) -> dict:
    total = Counter()
    for r in records:
        total.update(r[key])
    return dict(total.most_common())


def _counts(records: list, key: str, label: str) -> dict:
    return {"total": _leaf(sum(_tally(records, key).values()), label, "transcripts"),
            "by_name": _leaf(_tally(records, key), label, "transcripts")}


def _skill_log(path: Path, window: dict) -> dict:
    src = f"skill-usage.log ({path.name})"
    label = "mesuré" if path.exists() else "incomplet"
    rows = []
    for line in path.read_text(errors="replace").splitlines() if path.exists() else []:
        parts = line.split()
        if len(parts) >= 2:
            rows.append((parts[0][:10], parts[1], parts[2] if len(parts) > 2 else "untagged"))
    inside = [r for r in rows if window["from"] and window["from"] <= r[0] <= window["to"]]
    days = sorted(r[0] for r in rows)
    return {"range": {"from": days[0] if days else None, "to": days[-1] if days else None},
            "total": _leaf(len(rows), label, src),
            "in_window": _leaf(len(inside), label, src),
            "by_month": _leaf(dict(sorted(Counter(r[0][:7] for r in rows).items())), label, src),
            "by_source": _leaf(dict(Counter(r[2] for r in rows).most_common()), label, src),
            "by_skill_in_window": _leaf(dict(Counter(r[1] for r in inside).most_common()), label, src)}


def _session_logs(vault: Path, window: dict) -> dict:
    files = hits = 0
    by_rule = Counter()
    for f in glob.glob(str(vault / "inbox/daily/implementation/**/*.md"), recursive=True):
        day = os.path.basename(f)[:10]
        if not (window["from"] and window["from"] <= day <= window["to"]):
            continue
        files += 1
        for line in Path(f).read_text(errors="replace").splitlines():
            if line.startswith("**Pitfall hit:**"):
                hits += 1
                by_rule.update(RULE_ID.findall(line))
    src = "inbox/daily/implementation/**/*.md"
    return {"files": _leaf(files, "mesuré", src), "pitfall_hits": _leaf(hits, "mesuré", src),
            "hits_by_rule": _leaf(dict(by_rule.most_common()), "mesuré", src)}


def _rules(vault: Path, window: dict) -> dict:
    cmd = (f"git log --reverse -p -- {' '.join(RULE_FILES)}; rule definitions only (id ending a line); "
           "a rule moved between files in one commit is neutral, across commits it counts removed then added")
    try:
        if not (vault / ".git").exists():
            raise OSError("not a repo root")
        out = subprocess.run(["git", "-C", str(vault), "log", "--reverse", "--format=%x00%ad", "--date=short",
                              "-p", "--", *RULE_FILES], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        bad = _leaf(None, "incomplet", cmd)
        return {k: bad for k in ("added", "removed", "added_in_window", "removed_in_window")}
    seen, present = set(), set()
    added, removed = [], []  # commit dates
    for chunk in out.split("\0")[1:]:
        day, _, diff = chunk.partition("\n")
        lines = [ln for ln in diff.splitlines() if ln.startswith(("+", "-")) and not ln.startswith(("+++", "---"))]
        plus, minus = ({m[1] for ln in lines if ln[0] == c and not RETIRED.search(ln) and (m := RULE_DEF.search(ln))}
                       for c in "+-")
        added += [day] * len(plus - seen)
        removed += [day] * len((minus - plus) & present)
        seen |= plus
        present = (present | plus) - (minus - plus)

    def inside(days):
        return sum(1 for d in days if window["from"] and window["from"] <= d <= window["to"])
    return {"added": _leaf(len(added), "mesuré", cmd), "removed": _leaf(len(removed), "mesuré", cmd),
            "added_in_window": _leaf(inside(added), "mesuré", cmd),
            "removed_in_window": _leaf(inside(removed), "mesuré", cmd)}


def _sensors(vault: Path) -> dict:
    drafts = [p for p in (vault / "inbox/sensors").glob("*") if p.is_file()] if (vault / "inbox/sensors").is_dir() else []
    installed = sum(1 for c in HOOK_CONFIGS if (REPO_DIR / c).is_file()
                    for ln in (REPO_DIR / c).read_text(errors="replace").splitlines() if HOOK_COMMAND.match(ln))
    return {"drafts": _leaf(len(drafts), "mesuré", "inbox/sensors/*"),
            "installed": _leaf(installed, "mesuré", "lines with `command` in " + ", ".join(HOOK_CONFIGS))}


def history(projects_dir: Path, skill_log: Path, vault: Path) -> dict:
    """One aggregate over every main transcript, the skill log and the vault. Subagent transcripts are not sessions."""
    recs = [parse_session(p) for p in sorted(glob.glob(os.path.join(projects_dir, "*", "*.jsonl")))]
    failed = sum(1 for r in recs if r["metrics_status"] == "failed")
    recs = [r for r in recs if r["metrics_status"] != "failed"]
    days = sorted(r["date"][:10] for r in recs)
    window = {"from": days[0] if days else None, "to": days[-1] if days else None}
    n, captured = len(recs), sum(r["captured"] for r in recs)
    lab = "incomplet" if failed or any(r["metrics_status"] == "partial" for r in recs) else "mesuré"
    costs = [r["cost_usd"] for r in recs if r["cost_usd"] is not None]
    return {
        "window": window,
        "sessions": {
            "count": _leaf(n, lab, "transcripts"),
            "unreadable": _leaf(failed, "mesuré", "transcripts"),
            "partial": _leaf(sum(r["metrics_status"] == "partial" for r in recs), "mesuré", "transcripts"),
            "user_turns": _leaf(sum(r["user_turns"] for r in recs), lab, "transcripts"),
            "duration_s": _leaf(sum(r["duration_s"] for r in recs), lab, "transcripts"),
            "cost_usd": _leaf(round(sum(costs), 2), "mesuré" if len(costs) == n and lab == "mesuré" else "incomplet", "transcripts"),
            "by_project": _leaf(dict(Counter(r["project"] for r in recs).most_common()), lab, "transcripts"),
        },
        "capture_rate": _leaf(round(captured / n, 3) if n else None, "incomplet",
                              "transcripts: sessions with a capture skill call or an implementation-log write; a log written through Bash is unseen, so a lower bound"),
        "skills": _counts(recs, "skills", lab),
        "mcp": _counts(recs, "mcp", lab),
        "agents": _counts(recs, "agents", lab),
        "hook_refusals": {**_counts(recs, "hook_refusals", lab),
                          "by_guard": _leaf(_tally(recs, "hook_refusals"), lab, "transcripts"),
                          "permission": _leaf(sum(r["permission_refusals"] for r in recs), lab, "transcripts")},
        "skill_log": _skill_log(Path(skill_log), window),
        "session_logs": _session_logs(Path(vault), window),
        "rules": _rules(Path(vault), window),
        "sensors": _sensors(Path(vault)),
        "harness_sessions": _leaf(
            sum(1 for f in glob.glob(str(Path(vault) / "meta/harness-sessions/*.jsonl"))
                for ln in Path(f).read_text(errors="replace").splitlines() if ln.strip()),
            "mesuré", "meta/harness-sessions/*.jsonl"),
    }


# Same row regex as skills/capture/scripts/check_log.py (separate plugins, no shared import): keep both in sync.
LABEL = re.compile(r"\*\*[^*]+:\*\*")
ROW = re.compile(r"^- (.+?) · (.+?) · expected: (.+?) · check: (.+?)(?: · (verdict: .+))?$")


def pending_changes(vault: Path, min_age_days: int = 7) -> list:
    """Harness-change rows at least `min_age_days` old with no verdict, plus every malformed row (any age)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=min_age_days)).strftime("%Y-%m-%d")
    out = []
    for log in sorted(Path(vault).glob("inbox/daily/implementation/*/*.md")):
        date = log.name[:10]
        if not re.match(r"\d{4}-\d{2}-\d{2}-", log.name):
            continue
        in_rows = False
        for n, line in enumerate(log.read_text(errors="replace").splitlines(), 1):
            if line.startswith("**Harness changes:**"):
                in_rows = True
            elif line.startswith("## ") or LABEL.match(line):  # next label or heading ends the block; blank lines do not
                in_rows = False
            elif in_rows and line.startswith("- "):
                m = ROW.match(line)
                if not m:
                    out.append({"log": str(log), "line": n, "malformed": True})
                elif not m.group(5) and date <= cutoff:
                    out.append({"log": str(log), "line": n, "date": date, "component": m.group(1),
                                "change": m.group(2), "expected": m.group(3), "check": m.group(4)})
    return out


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
    h = sub.add_parser("history")
    h.add_argument("--vault", required=True)
    h.add_argument("--projects", default=os.environ.get("CLAUDE_PROJECTS_DIR") or "~/.claude/projects")
    h.add_argument("--skill-log", default="~/.claude/skill-usage.log")
    c = sub.add_parser("changes")
    c.add_argument("--vault", required=True)
    c.add_argument("--days", type=int, default=7)
    args = ap.parse_args(argv)
    if args.cmd == "changes":
        print(json.dumps(pending_changes(Path(args.vault), args.days), ensure_ascii=False, indent=1))
        return 0
    if args.cmd == "history":
        agg = history(Path(args.projects).expanduser(), Path(args.skill_log).expanduser(), Path(args.vault))
        print(json.dumps(agg, ensure_ascii=False, indent=1))
        return 0
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
