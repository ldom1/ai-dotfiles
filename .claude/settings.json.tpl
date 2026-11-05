{
  "model": "opus[1m]",
  "preferredNotifChannel": "terminal_bell",
  "env": {
    "CLAUDE_CODE_SUBAGENT_MODEL": "sonnet",
    "GRAPHIFY_NO_AUTO_REFRESH": "1"
  },
  "permissions": {
    "deny": [
      "Bash(git push --force *)",
      "Bash(git push --no-verify*)",
      "Bash(git push * --no-verify*)",
      "Bash(git -C * push*--no-verify*)",
      "Bash(git -c core.hooksPath*)",
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
      },
      {
        "hooks": [
          {
            "type": "command",
            "command": "__HOME__/.local/bin/aif-agent-hook",
            "timeout": 5
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
      },
      {
        "hooks": [
          {
            "type": "command",
            "command": "__HOME__/.local/bin/aif-agent-hook",
            "timeout": 5
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
            "command": "__HOME__/.claude/hooks/local-ci-merge-guard.py"
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
      },
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "__HOME__/.local/bin/aif-agent-hook",
            "timeout": 5
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
      },
      {
        "hooks": [
          {
            "type": "command",
            "command": "__HOME__/.local/bin/aif-agent-hook",
            "timeout": 5
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
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "__HOME__/.local/bin/aif-agent-hook",
            "timeout": 5
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "__HOME__/.local/bin/aif-agent-hook",
            "timeout": 5
          }
        ]
      }
    ],
    "PostToolUseFailure": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "__HOME__/.local/bin/aif-agent-hook",
            "timeout": 5
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "permission_prompt|elicitation_dialog",
        "hooks": [
          {
            "type": "command",
            "command": "__HOME__/.local/bin/aif-agent-hook",
            "timeout": 5
          }
        ]
      }
    ],
    "StopFailure": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "__HOME__/.local/bin/aif-agent-hook",
            "timeout": 5
          }
        ]
      }
    ],
    "SubagentStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "__HOME__/.local/bin/aif-agent-hook",
            "timeout": 5
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "__HOME__/.local/bin/aif-agent-hook",
            "timeout": 5
          }
        ]
      }
    ]
  },
  "statusLine": {
    "type": "command",
    "command": "__HOME__/.local/bin/aif-statusline __HOME__/.local/bin/ccstatusline --config __HOME__/.claude/ccstatusline-settings.json",
    "padding": 2,
    "refreshInterval": 10
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
