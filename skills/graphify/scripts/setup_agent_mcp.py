#!/usr/bin/env python3
"""Merge graphify MCP server entries into Cursor and Claude Code project configs."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


GRAPHIFY_SERVER_NAME = "graphify"
GRAPH_REL = "graphify-out/graph.json"


def _merge_mcp_file(path: Path, entry: dict) -> bool:
    data: dict = {"mcpServers": {}}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data = loaded
        except json.JSONDecodeError:
            print(f"warning: {path} is invalid JSON — backing up and rewriting", file=sys.stderr)
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))

    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        servers = {}
        data["mcpServers"] = servers

    prev = servers.get(GRAPHIFY_SERVER_NAME)
    servers[GRAPHIFY_SERVER_NAME] = entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    action = "updated" if prev else "added"
    print(f"  {path}: {action} {GRAPHIFY_SERVER_NAME}")
    return True


def _ensure_mcp_extra(root: Path) -> None:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists() or shutil.which("uv") is None:
        return
    subprocess.run(
        ["uv", "add", "graphifyy[mcp]"],
        cwd=root,
        check=False,
    )


def _mcp_entry(root: Path, graph_path: Path) -> dict:
    rel_graph = graph_path.relative_to(root).as_posix()
    if (root / "pyproject.toml").exists() and shutil.which("uv"):
        return {
            "command": "uv",
            "args": ["run", "python", "-m", "graphify.serve", rel_graph],
        }
    python = root / "graphify-out" / ".graphify_python"
    if python.exists():
        cmd = python.read_text(encoding="utf-8").strip()
        if cmd == "uv run python":
            return {
                "command": "uv",
                "args": ["run", "python", "-m", "graphify.serve", rel_graph],
            }
        return {
            "command": cmd,
            "args": ["-m", "graphify.serve", rel_graph],
        }
    return {
        "command": "python3",
        "args": ["-m", "graphify.serve", rel_graph],
    }


def _run_central_mcp_sync() -> None:
    """Ensure graphify (plus qmd, code-index) is registered globally for Claude Code.

    graphify's Claude Code entry is identical across every project — it resolves the
    graph path via ${CLAUDE_PROJECT_DIR} at runtime instead of a baked-in path — so
    it's centrally managed by ai-dotfiles rather than written per-project. This just
    (re)applies that central template; safe and idempotent from any project.
    """
    ai_dotfiles = Path(__file__).resolve().parents[3]
    mcp_sync = ai_dotfiles / "scripts" / "mcp-sync.sh"
    if not mcp_sync.exists():
        print(
            f"warning: {mcp_sync} not found — Claude Code graphify registration skipped; "
            "run 'ai-dotfiles mcp-sync' manually",
            file=sys.stderr,
        )
        return
    subprocess.run(["bash", str(mcp_sync)], check=False)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    graph_path = root / GRAPH_REL
    if not graph_path.exists():
        print(f"error: {graph_path} not found — run /graphify first", file=sys.stderr)
        return 1

    _ensure_mcp_extra(root)
    entry = _mcp_entry(root, graph_path)

    print(f"Configuring graphify MCP for {root}")
    _merge_mcp_file(root / ".cursor" / "mcp.json", entry)
    _run_central_mcp_sync()
    print("Restart Cursor / Claude Code (or start a new session) to load the graphify MCP server.")
    print("Tools: query_graph, get_node, get_neighbors, shortest_path, god_nodes, graph_stats, …")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
