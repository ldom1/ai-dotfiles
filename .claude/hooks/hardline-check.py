#!/usr/bin/env python3
"""PreToolUse (Bash): hardline tripwire for a short list of destructive commands.

This is a tripwire, not a security boundary: the sandbox or the OS user is the boundary.
Tier deny (irreversible): rm -rf on / or home, mkfs, dd or a redirect to a device, find -delete from
/ or home, fork bomb. The user can still run the command with `! <cmd>`.
Tier ask (recoverable): force push to main, git clean -x/-d, docker prune, chmod -R 777, curl | sh,
and tier-1 shapes whose target holds $ or a backtick. Unbalanced quotes ask only if rm, dd or mkfs appears.
Rules: hardline-rules.json (JSON, not TOML: tomllib needs Python 3.11, and python3 here can be 3.10).

Parsing: heredoc bodies are data and are dropped (a body fed to bash/sh/zsh is parsed one level deep).
shlex (punctuation_chars) splits simple commands. VAR=x and wrappers are skipped, /bin/rm becomes rm,
and `bash|sh|zsh -c` and `rtk proxy '...'` are parsed one level deep.

Known bypasses (not covered; tests/test_hardline_check.py asserts that they pass):
- variable expansion: `D=/; rm -rf $D` only asks, `F=-rf; rm $F /` passes;
- other interpreters: `python3 -c 'import shutil; shutil.rmtree(...)'`;
- a script written to a file, then run;
- nested `bash -c` deeper than one level;
- aliases and shell functions.

Rule fields: program (globs), subcommand (word lists), option_values (options that take a value),
flags (groups of alternatives, every group needed; `-x` also matches inside `-xyz`), unless (flags that
exempt), targets (exact) and target_globs on positional args, target_prefix (`of=`), leading_only (args
before the first option), no_targets, dynamic (decision for a $ or ` target), redirect_globs (file after
> or >>), pipe_from (programs piped into a shell), raw_regex (on the command without heredoc bodies).
"""
import io, json, os, re, shlex, sys  # noqa: E401
from fnmatch import fnmatchcase

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "hardline-rules.json")) as _f:
    CFG = json.load(_f)
SHELLS, RANK, PUNCT = CFG["shells"], {"ask": 1, "deny": 2}, set(";&|()<>\n")
HEREDOC = re.compile(r"(?<!<)<<(-?)[ \t]*(['\"]?)\\?([A-Za-z_][\w.-]*)\2")


def strip_heredocs(cmd):
    """Replace each heredoc operator with `<< __hdN__` and drop its body. Return (cmd, bodies)."""
    out, bodies, pending = [], [], []

    def placeholder(m):
        pending.append((m[1], m[3], len(bodies)))
        bodies.append([])
        return f"<< __hd{len(bodies) - 1}__"
    for line in cmd.split("\n"):
        if pending:
            dash, delim, i = pending[0]
            pending.pop(0) if (line.lstrip("\t") if dash else line) == delim else bodies[i].append(line)
        else:
            out.append(HEREDOC.sub(placeholder, line))
    return "\n".join(out), ["\n".join(b) for b in bodies]


class _Lines(io.StringIO):
    def readline(self, size=-1):  # shlex skips a comment with readline(): keep its newline as an operator
        s, pos = self.getvalue(), self.tell()
        end = s.find("\n", pos)
        end = len(s) if end < 0 else end
        self.seek(end)
        return s[pos:end]


def commands(cmd):
    """Split into simple commands: dicts of op (operator before it), words, redirs. Raises ValueError."""
    lex = shlex.shlex(_Lines(re.sub(r"(?<=[^\s;&|()<>])#", "_", cmd)), posix=True, punctuation_chars=";&|()<>\n")
    lex.whitespace, lex.whitespace_split = " \t\r", True
    toks = iter(list(lex))
    cur = {"op": "", "words": [], "redirs": []}
    out = [cur]
    for t in toks:
        if not (t and set(t) <= PUNCT):
            cur["words"].append(t)
        elif (">" in t or "<" in t) and not t.endswith("("):
            cur["redirs"].append((t, next(toks, "")))
        else:
            cur = {"op": t.strip(), "words": [], "redirs": []}
            out.append(cur)
    return [c for c in out if c["words"]]


def resolve(c, bodies):
    """Skip VAR=x and wrappers. Return (program, args, payloads to parse one level deeper)."""
    w = list(c["words"])
    while w:
        if re.match(r"[A-Za-z_]\w*=", w[0]):
            w.pop(0)
            continue
        skip = next((s.split() for s in CFG["skip"] if w[:len(s.split())] == s.split()), None)
        if not skip:
            break
        w = w[len(skip):]
        while w and (w[0].startswith("-") or re.fullmatch(r"[\d.]+[smhd]?", w[0])):
            w.pop(0)
        if skip == ["rtk", "proxy"] and len(w) == 1 and " " in w[0]:
            return "", [], w
    if not w:
        return "", [], []
    prog, args, payloads = os.path.basename(w[0]) if "/" in w[0] else w[0], w[1:], []
    if prog in SHELLS:
        for i, a in enumerate(args):
            if not a.startswith("-"):
                break
            if re.fullmatch(r"-[A-Za-z]*c[A-Za-z]*", a) and i + 1 < len(args):
                payloads.append(args[i + 1])
        payloads += [bodies[int(t[4:-2])] for op, t in c["redirs"] if op == "<<" and re.fullmatch(r"__hd\d+__", t)]
    return prog, args, payloads


def has(opts, alt):
    if len(alt) == 2:
        return any(re.fullmatch(r"-[A-Za-z0-9]+", o) and alt[1] in o[1:] for o in opts)
    return any(o == alt or o.startswith(alt + "=") for o in opts)


def match(r, prog, args, c, prev):
    if "redirect_globs" in r:
        return any(">" in op and any(fnmatchcase(t, g) for g in r["redirect_globs"]) for op, t in c["redirs"])
    if "pipe_from" in r:
        return c["op"] in ("|", "|&") and prog in SHELLS and prev in r["pipe_from"]
    if not any(fnmatchcase(prog, g) for g in r.get("program", [])):
        return False
    opts, pos, it = [], [], iter(args)
    for a in it:
        if a == "--":
            pos += list(it)
        elif a.startswith("-") and len(a) > 1:
            opts.append(a)
            next(it, None) if a in r.get("option_values", []) else None
        else:
            pos.append(a)
    sub = next((s for s in r.get("subcommand", [[]]) if pos[:len(s)] == s), None)
    if sub is None or not all(any(has(opts, a) for a in g) for g in r.get("flags", [])):
        return False
    if any(has(opts, a) for a in r.get("unless", [])):
        return False
    cand = pos[len(sub):]
    if r.get("leading_only"):
        cand = [a for a in args[:next((i for i, a in enumerate(args) if a[:1] in "-(!"), len(args))]]
    pre = r.get("target_prefix", "")
    cand = [a[len(pre):] for a in cand if a.startswith(pre)]
    if r.get("no_targets"):
        return not cand
    if "targets" not in r and "target_globs" not in r:
        return True
    norm = [a.rstrip("/") or a for a in cand]
    if any(a in r.get("targets", []) or any(fnmatchcase(a, g) for g in r.get("target_globs", [])) for a in norm):
        return True
    return "dynamic" if r.get("dynamic") and any("$" in a or "`" in a for a in cand) else False


def classify(cmd, depth=0):
    """Return (decision, rule_id, why) for the most severe hit, or None."""
    cmd, bodies = strip_heredocs(cmd.replace("\\\n", ""))
    hits = [(r["tier"], r["id"], r["why"]) for r in CFG["rules"] if re.search(r.get("raw_regex", "$^"), cmd)]
    try:
        cmds = commands(cmd)
    except ValueError:
        cmds = []
        if re.search(r"\b(rm|dd|mkfs)", cmd):
            hits.append(("ask", "unparsed", "unbalanced quotes near rm, dd or mkfs"))
    prev = None
    for c in cmds:
        prog, args, payloads = resolve(c, bodies)
        hits += [classify(p, 1) for p in payloads if depth == 0]
        for r in CFG["rules"]:
            m = match(r, prog, args, c, prev)
            if m == "dynamic":
                hits.append((r["dynamic"], r["id"] + "-dynamic", r["why"] + ", target not readable statically"))
            elif m:
                hits.append((r["tier"], r["id"], r["why"]))
        prev = prog
    return max(filter(None, hits), key=lambda h: RANK[h[0]], default=None)


def main():
    cmd = (json.load(sys.stdin).get("tool_input") or {}).get("command") or ""
    hit = classify(cmd)
    if not hit:
        return
    tier, rid, why = hit
    reason = f"hardline-check {rid}: {why}."
    if tier == "deny":
        shown = cmd if len(cmd) <= 200 and "\n" not in cmd else "<command>"
        reason += f" Not run. If the user wants it, they run it themselves with `! {shown}`."
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": tier,
                                             "permissionDecisionReason": reason}}))


if __name__ == "__main__":
    main()
