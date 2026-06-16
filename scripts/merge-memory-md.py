#!/usr/bin/env python3
"""Backfill an existing memory markdown file with structure added to its template since init.

Usage: merge-memory-md.py <template-path> <dest-path>
Prints "changed" or "unchanged" and writes dest-path in place if changed.
Never touches existing content — only adds a missing frontmatter block and
any "## Section" headers present in the template but absent from dest.
"""
import re
import sys

tpl_path, dest_path = sys.argv[1], sys.argv[2]
tpl = open(tpl_path).read()
dest = open(dest_path).read()
changed = False

frontmatter = re.match(r"^---\n.*?\n---\n", tpl, re.S)
if frontmatter and not dest.startswith("---\n"):
    dest = frontmatter.group(0) + "\n" + dest
    changed = True

tpl_headers = re.findall(r"^(## .+)$", tpl, re.M)
dest_headers = set(re.findall(r"^(## .+)$", dest, re.M))
missing = [h for h in tpl_headers if h not in dest_headers]
if missing:
    if not dest.endswith("\n"):
        dest += "\n"
    for header in missing:
        dest += f"\n{header}\n<!-- added by ai-dotfiles upgrade -->\n"
    changed = True

if changed:
    open(dest_path, "w").write(dest)
    print("changed")
else:
    print("unchanged")
