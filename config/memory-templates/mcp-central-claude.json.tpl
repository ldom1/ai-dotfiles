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
      "args": ["code-index-mcp", "--project-path", "${CLAUDE_PROJECT_DIR}"]
    },
    "graphify": {
      "command": "uv",
      "args": [
        "run", "--project", "${CLAUDE_PROJECT_DIR}",
        "python", "-m", "graphify.serve",
        "${CLAUDE_PROJECT_DIR}/graphify-out/graph.json"
      ]
    }
  }
}
