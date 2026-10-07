{
  "model": "opus[1m]",
  "env": {
    "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet"
  },
  "permissions": {
    "deny": [
      "Bash(git push --force *)",
      "Bash(git reset --hard *)",
      "Bash(git checkout . *)",
      "Bash(git checkout -- *)",
      "Bash(git clean -f *)",
      "Bash(rm -rf *)",
      "Bash(stop-check-trust *)",
      "Bash(*/stop-check-trust *)"
    ],
    "ask": [
      "Bash(ansible-playbook *)",
      "Bash(kubectl apply *)",
      "Bash(kubectl delete *)",
      "Bash(docker compose down *)",
      "Bash(terraform apply *)",
      "Bash(terraform destroy *)"
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
            "command": "__HOME__/.claude/hooks/hardline-check.py"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "__HOME__/.claude/hooks/rtk-rewrite.sh"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "__HOME__/.claude/hooks/git-commit-check.sh"
          }
        ]
      },
      {
        "matcher": "Skill",
        "hooks": [
          {
            "type": "command",
            "command": "__HOME__/.claude/hooks/log-skill-usage.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "__HOME__/.claude/hooks/stop-check.sh",
            "timeout": 180
          },
          {
            "type": "command",
            "command": "__HOME__/.claude/hooks/compact-nudge.sh"
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "__HOME__/.claude/hooks/precompact-checkpoint.sh"
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
    "code-simplifier@claude-plugins-official": true,
    "skill-creator@claude-plugins-official": true,
    "impeccable@impeccable": false,
    "taste-skill@taste-skill": false
  },
  "extraKnownMarketplaces": {
    "impeccable": {
      "source": {
        "source": "github",
        "repo": "pbakaus/impeccable"
      }
    },
    "taste-skill": {
      "source": {
        "source": "github",
        "repo": "Leonxlnx/taste-skill"
      }
    }
  }
}
