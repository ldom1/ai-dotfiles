# RTK — token proxy

**rtk** rewrites common dev commands so outputs stay small. The **PreToolUse** hook calls `rtk rewrite` before **FinOps tail caps** on noisy installs/builds (`hooks/rtk-rewrite.sh`).

## Commands

```bash
rtk gain              # savings summary
rtk gain --history
rtk discover          # missed opportunities in Claude history
rtk proxy '<cmd>'    # run without rewrite
rtk --version
```

**Collision:** if `rtk gain` fails, you may have the wrong `rtk` on PATH.

## Full doc

Vault: `$BRAIN_PATH/resources/knowledge/operational/rtk.md`.
