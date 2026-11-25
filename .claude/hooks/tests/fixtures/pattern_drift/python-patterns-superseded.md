---
title: Python patterns superseded
---

# Python patterns superseded

## Superseded
- ~~Config: module-level UPPER_CASE constants in `config.py`, imported directly.~~ → ^p31 (2026-11-25, pydantic-settings: typed, env and CLI overrides, one source) ^p4
  detect:
    lang: python
    files: ["**/config.py"]
    rule: |
      id: config-constants
      language: python
      rule:
        kind: expression_statement
        inside:
          kind: module
          stopBy: neighbor
        has:
          kind: assignment
          has:
            field: left
            kind: identifier
            regex: '^[A-Z][A-Z0-9_]+$'
          all:
            - has:
                field: right
                any:
                  - kind: string
                  - kind: integer
                  - kind: float
                  - kind: dictionary
                  - kind: list
                  - kind: tuple
                  - kind: "true"
                  - kind: "false"
    absent_in_repo: "class $C(BaseSettings): $$$B"
