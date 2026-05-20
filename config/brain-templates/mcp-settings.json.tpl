{
  "mcpServers": {
    "code-index": {
      "command": "uvx",
      "args": ["code-index-mcp", "--project-path", "__PROJECT_PATH__"]
    },
    "qmd": {
      "command": "qmd",
      "args": ["mcp"],
      "env": {
        "INDEX_PATH": "__QMD_INDEX_PATH__"
      }
    }
  }
}
