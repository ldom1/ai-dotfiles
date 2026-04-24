{
  "model": "opus[1m]",
  "permissions": {
    "deny": [
      "Bash(git push --force *)",
      "Bash(git reset --hard *)",
      "Bash(git checkout . *)",
      "Bash(git checkout -- *)",
      "Bash(git clean -f *)",
      "Bash(rm -rf *)"
    ]
  },
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "__HOME__/.claude/hooks/brain-session-start.sh"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "__HOME__/.claude/hooks/brain-session-end.sh",
            "timeout": 120
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "__HOME__/.claude/hooks/rtk-rewrite.sh"
          }
        ]
      }
    ]
  },
  "statusLine": {
    "type": "command",
    "command": "npx -y ccstatusline@latest --config __HOME__/.claude/ccstatusline-settings.json",
    "padding": 2
  },
  "enabledPlugins": {
    "superpowers@claude-plugins-official": true,
    "frontend-design@claude-plugins-official": true,
    "code-simplifier@claude-plugins-official": true,
    "skill-creator@claude-plugins-official": true
  },
  "skipDangerousModePermissionPrompt": true
}
