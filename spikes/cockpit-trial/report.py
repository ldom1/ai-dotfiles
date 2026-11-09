#!/usr/bin/env -S python3 -I
"""Cockpit trial report: join ai-dotdeck waits with the states Herdr showed (plan 2026-11-09, Task 4).

Usage: report.py [--check-log PATH] [--trial-log PATH] [--step SECONDS]
       report.py monitor [--session NAME] [--trial-log PATH] [--interval 1]
- monitor polls `herdr agent list` (about 2 ms per call) and appends one row per changed pane; a pane
  that leaves the list gets state "gone". Herdr events need one subscription per pane_id, so polling
  is simpler. The list carries no question text: text_shown is noted by hand in the trial grid.
- Waits come from aif-check.log (epoch, session, enter|leave, ask, pane key). Only Herdr pane keys
  (herdr-...) count; tmux panes and old 4-column lines are skipped.
- Herdr rows come from cockpit-trial.jsonl, one line per change: {"ts", "pane", "state", "message"}.
Rules:
- Join: wait key "herdr-<x>" with the Herdr pane whose id, outside [A-Za-z0-9] replaced by "-", is <x>.
- Window: [enter - 1 s, leave + 1 s]. Seen: the Herdr state is "blocked" at some time in the window
  (the last row before the window counts: Herdr writes a row only on change).
- too_short: a wait shorter than 2 x step is neither seen nor missed (step 0 = event mode: never).
- An enter with no leave ends at the next enter on that pane, or at the end of the log.
- text_shown: seen, and a blocked row in the window carries a message.
- false_blocked: a Herdr "blocked" start outside every wait window of that pane.
"""
import argparse
import json
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

SLACK = 1.0


@dataclass
class Wait:
    key: str
    ask: str
    enter: float
    leave: float


@dataclass
class Row:
    ts: float
    pane: str
    state: str
    message: str | None = None


@dataclass
class Counts:
    waits: int = 0
    seen: int = 0
    text_shown: int = 0
    missed: int = 0
    too_short: int = 0
    false_blocked: int = 0


def pane_key(pane: str) -> str:
    return "herdr-" + re.sub(r"[^A-Za-z0-9]", "-", pane)


def parse_check_log(text: str, end: float) -> list[Wait]:
    waits: list[Wait] = []
    open_: dict[str, Wait] = {}
    for line in text.splitlines():
        f = line.split("\t")
        if len(f) < 5 or not f[0].isdigit() or not f[4].startswith("herdr-"):
            continue
        ts, kind, ask, key = float(f[0]), f[2], f[3], f[4]
        if key in open_:
            open_.pop(key).leave = ts
        if kind == "enter":
            open_[key] = Wait(key=key, ask=ask, enter=ts, leave=end)
            waits.append(open_[key])
    return waits


def match_waits(waits: list[Wait], rows: list[Row], step_s: float) -> dict[str, Counts]:
    by_key: dict[str, list[Row]] = {}
    for row in sorted(rows, key=lambda x: x.ts):
        by_key.setdefault(pane_key(row.pane), []).append(row)
    out: dict[str, Counts] = {"_all": Counts()}
    for wait in waits:
        c = out.setdefault(wait.ask, Counts())
        c.waits += 1
        if step_s and wait.leave - wait.enter < 2 * step_s:
            c.too_short += 1
            continue
        lo, hi = wait.enter - SLACK, wait.leave + SLACK
        pane_rows = by_key.get(wait.key, [])
        before = [x for x in pane_rows if x.ts < lo]
        inside = [x for x in pane_rows if lo <= x.ts <= hi]
        blocked = [x for x in ([before[-1]] if before else []) + inside if x.state == "blocked"]
        if blocked:
            c.seen += 1
            c.text_shown += any(x.message for x in blocked)
        else:
            c.missed += 1
    windows = [(w.key, w.enter - SLACK, w.leave + SLACK) for w in waits]
    for key, pane_rows in by_key.items():
        prev = None
        for row in pane_rows:
            if row.state == "blocked" and prev != "blocked" and not any(
                    k == key and lo <= row.ts <= hi for k, lo, hi in windows):
                out["_all"].false_blocked += 1
            prev = row.state
    return out


def rows_from_agent_list(text: str, ts: float) -> list[Row]:
    agents = json.loads(text)["result"]["agents"]
    return [Row(ts=ts, pane=a["pane_id"], state=a["agent_status"]) for a in agents]


def changes(prev: dict[str, str], cur: dict[str, str], ts: float) -> list[Row]:
    out = [Row(ts=ts, pane=p, state=s) for p, s in cur.items() if prev.get(p) != s]
    return out + [Row(ts=ts, pane=p, state="gone") for p in prev if p not in cur]


def monitor(session: str | None, trial_log: Path, interval: float) -> None:
    cmd = ["herdr"] + (["--session", session] if session else []) + ["agent", "list"]
    prev: dict[str, str] = {}
    trial_log.parent.mkdir(parents=True, exist_ok=True)
    while True:
        now = time.time()
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            cur = {x.pane: x.state for x in rows_from_agent_list(res.stdout, now)}
            with trial_log.open("a") as f:
                for row in changes(prev, cur, now):
                    f.write(json.dumps(row.__dict__) + "\n")
            prev = cur
        time.sleep(interval)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", nargs="?", choices=["report", "monitor"], default="report")
    ap.add_argument("--session")
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--check-log", default="~/.claude/logs/aif-check.log")
    ap.add_argument("--trial-log", default="~/.claude/logs/cockpit-trial.jsonl")
    ap.add_argument("--step", type=float, default=1.0)
    a = ap.parse_args()
    if a.mode == "monitor":
        monitor(a.session, Path(a.trial_log).expanduser(), a.interval)
        return
    waits = parse_check_log(Path(a.check_log).expanduser().read_text(), end=time.time())
    rows = [Row(**json.loads(x)) for x in Path(a.trial_log).expanduser().read_text().splitlines() if x.strip()]
    counts = match_waits(waits, rows, a.step)
    for ask, c in sorted(counts.items()):
        print(ask, json.dumps(c.__dict__))


if __name__ == "__main__":
    main()
