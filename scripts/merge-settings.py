#!/usr/bin/env python3
"""Merge settings.json.tpl into a live settings.json. Fail closed on semantic conflicts.

Usage: merge-settings.py [--dry-run] TEMPLATE SETTINGS   (__HOME__ in TEMPLATE renders as $HOME)
Owned keys: enabledPlugins, extraKnownMarketplaces, permissions.deny/ask, env, hooks. Adds missing
template entries, keeps live-only ones. Semantic conflict (env value differs; same hook command with
another event/matcher/timeout; live disableAllHooks): prints CONFLICT lines, writes nothing, exits 3.
"""
import copy, json, os, shutil, sys, tempfile  # noqa: E401


def hook_entries(hooks):
    for event, groups in (hooks or {}).items():
        for group in groups:
            for h in group.get("hooks", []):
                yield event, group.get("matcher"), h


def where(event, matcher, timeout):
    return f'"{event} matcher={matcher} timeout={timeout}"'


def plan(tpl, cur):
    out, adds, notes, conflicts = copy.deepcopy(cur), [], [], []
    for key in ("enabledPlugins", "extraKnownMarketplaces"):
        for name, val in tpl.get(key, {}).items():
            if cur.get(key, {}).get(name) != val:
                out.setdefault(key, {})[name] = val
                adds.append(f"{key}.{name}: {json.dumps(val)}")
    allow = cur.get("permissions", {}).get("allow", [])
    for kind in ("deny", "ask"):
        for rule in tpl.get("permissions", {}).get(kind, []):
            if rule in allow:
                notes.append(f"note: {rule} is also in live allow; the template rule wins")
            if rule not in out.get("permissions", {}).get(kind, []):
                out.setdefault("permissions", {}).setdefault(kind, []).append(rule)
                adds.append(f"permissions.{kind}: {rule}")
    live_env = cur.get("env", {})
    for name, val in tpl.get("env", {}).items():
        if name not in live_env:
            out.setdefault("env", {})[name] = val
            adds.append(f"env.{name}: {json.dumps(val)}")
        elif live_env[name] != val:
            conflicts.append(f"CONFLICT env.{name}: live={json.dumps(live_env[name])} template={json.dumps(val)}"
                             " → edit settings.json to the template value, or remove the key from the template")
    if cur.get("disableAllHooks") is True and tpl.get("hooks"):
        conflicts.append("CONFLICT disableAllHooks: live=true template=unset"
                         " → remove disableAllHooks from settings.json, or no template hook runs")
    live_hooks = {}
    for event, matcher, h in hook_entries(cur.get("hooks")):
        live_hooks.setdefault(h.get("command"), []).append((event, matcher, h.get("timeout")))
    for event, matcher, h in hook_entries(tpl.get("hooks")):
        want, seen = (event, matcher, h.get("timeout")), live_hooks.get(h["command"])
        if seen is None:
            group = {"matcher": matcher, "hooks": [h]} if matcher is not None else {"hooks": [h]}
            out.setdefault("hooks", {}).setdefault(event, []).append(group)
            adds.append(f"hooks.{event}: {h['command']}")
        elif want not in seen:
            conflicts.append(f"CONFLICT hooks.{event} {h['command']}: live={where(*seen[0])} template={where(*want)}"
                             " → set the live hook to the template event, matcher and timeout, or change the template")
    return out, adds, notes, conflicts


def write_atomic(path, data):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)), prefix=".settings.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        with open(tmp) as f:
            json.load(f)
        if os.path.exists(path):
            shutil.copymode(path, tmp)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def main(argv):
    dry = "--dry-run" in argv
    tpl_path, path = [a for a in argv if a != "--dry-run"]
    with open(tpl_path) as f:
        tpl = json.loads(f.read().replace("__HOME__", os.environ["HOME"]))
    if not os.path.exists(path):
        print(f"add {path}: create from template")
        if not dry:
            write_atomic(path, tpl)
        return 0
    with open(path) as f:
        out, adds, notes, conflicts = plan(tpl, json.load(f))
    for line in [f"add {a}" for a in adds] + notes + conflicts:
        print(line)
    if conflicts:
        print(f"{len(conflicts)} conflict(s): {path} unchanged. Resolve them, then run install.sh again.")
        return 3
    if not adds:
        print(f"no changes: {path} has every template entry")
    elif not dry:
        shutil.copy2(path, path + ".bak")
        write_atomic(path, out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
