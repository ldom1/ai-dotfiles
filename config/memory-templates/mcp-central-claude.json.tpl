{
  "mcpServers": {
    "qmd": {
      "command": "qmd",
      "args": ["mcp"],
      "env": {
        "INDEX_PATH": "__QMD_INDEX_PATH__"
      }
    },
    "code-index": {
      "command": "uvx",
      "args": ["code-index-mcp", "--project-path", "${CLAUDE_PROJECT_DIR:-.}"]
    },
    "graphify": {
      "command": "uvx",
      "args": [
        "--from", "graphifyy[mcp]==0.9.79",
        "python", "-m", "graphify.serve",
        "${CLAUDE_PROJECT_DIR:-.}/graphify-out/graph.json"
      ]
    }
  }
}
