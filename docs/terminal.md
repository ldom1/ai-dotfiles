# ai-dotdeck: tmux and aif-sidebar

ai-dotdeck is the agent session harness of ai-dotfiles, on the terminal side: one tmux session per project, and a sidebar that shows sessions, agents and actions. Back to the [README](../README.md).

## tmux for agents

`install.sh` links `~/.tmux.conf` to `config/tmux.conf`, installs `bin/tma` in `~/.local/bin` and clones [TPM](https://github.com/tmux-plugins/tpm).

Terminal init: `install.sh` adds one line to `~/.zshrc` and `~/.bashrc` (or to the rc file of the login shell when neither exists). The line sources `config/shell-init.sh`:

- It puts `~/.local/bin` on `PATH`.
- A new terminal outside tmux runs `tma`: it opens the session of the current folder (`main` for `~`). After a detach, the shell continues.
- It does not run `tma` inside tmux, in the VS Code or Cursor terminal, in a shell started by Claude Code, without a tty, or in a shell that runs a command (`zsh -lic tma`).
- Set `AIF_NO_TMUX=1` to turn it off.
The sidebar is `aif-sidebar` (Rust + ratatui, `sidebar/`; decision: [`docs/adr/0001-agents-sidebar.md`](adr/0001-agents-sidebar.md)): one pane on the left of each window, with the sessions, the Claude Code agents and the actions.

Platforms:

- WSL with Windows Terminal (Ubuntu 22.04+, tmux 3.2a+), and native Ubuntu 26.04 with Ghostty (GNOME, Wayland, tmux 3.6a).
- `bin/aif-platform` holds every platform difference: `name` (`wsl` or `linux`), `copy`, `notify`, `open`. `AIF_PLATFORM=wsl|linux` forces the platform.
- `config/tmux.conf` loads `config/tmux-platform-<name>.conf`: Windows Terminal keys on WSL; Wayland clipboard and Ghostty features on Linux.
- Options newer than tmux 3.2a are guarded by `%if #{>=:#{version},X}` (for example `extended-keys-format csi-u` from 3.5).
- Native Linux: `install.sh` checks `wl-copy`, `notify-send`, `jq` and `fzf`, installs JetBrainsMono Nerd Font in `~/.local/share/fonts`, and links `~/.config/ghostty/config` when Ghostty is installed.
- WSL: `install.sh` checks `jq` and `fzf`. For Windows notifications, run once in Windows PowerShell: `Install-Module BurntToast -Scope CurrentUser`.

Sessions:

- `tma [dir]` attaches to the session for `dir`, or creates it. The session name is the folder name (`main` for `~`).
- `tma -n <name> [dir]` sets the name. Use it for an SSH session (`tma -n vps`).
- If a session of the same name exists for another folder, `tma` stops and shows both paths. Use `-n`.
- A session created without a name (plain `tmux`) is renamed after its folder by `config/tmux-name-session.sh` (`after-new-session` hook), with a `-2` suffix when the name is taken.
- `+ Terminal` in the sidebar (or `T`) opens a new session in `~` and switches to it. It gets the name of an unnamed session: `main`, or `main-2` when `main` exists.
- `Ctrl+Shift+N` (or `prefix N`) opens the New session screen in the sidebar. It lists folders from `zoxide`, or else the git repositories under `~` (3 levels). Each folder shows `new`, `attach <session>` (a session is open on it) or `name taken → <name>-2` (the name belongs to another folder: the new session gets a `-2` suffix). A typed path (`~/…`, `/…`, or `lab/x` relative to `~`) that does not exist is created with `git init`.
- `+` in the sidebar (or `prefix +`, or `+ New project`) opens the New project screen. Type a name: the project goes into the folder that holds the most of your projects (for example `~/lab`). `Create & open` creates the folder, runs `git init` and opens a session in it.
- `Ctrl+Shift+X` closes the current pane. It asks first when an agent (`claude`) runs in the pane. It does nothing in the sidebar.
- `Ctrl+Shift+K` (or `prefix X`) opens the Kill session screen: it lists the agents that will stop. `Save & kill` saves the layout first, so the session does not come back on restore, then kills it.
- `prefix Q` opens the Save & exit screen: save every session, then quit tmux. `d` there detaches instead: sessions and agents keep running.
- Right click on a session in the sidebar opens its menu: switch, rename, kill, new terminal, new session, new project, hide sidebar. Elsewhere in the sidebar, the menu is for the current session.
- Right click on an agent (AGENTS tab, or an agent row in the SESSIONS tree) opens the menu of that agent: go to agent, peek, reply (when it waits), interrupt (when it runs), and `Session menu…` for the session of the agent.
- A renamed session no longer matches its folder: `tma <dir>` then creates a new session with the folder name.

Keys:

- `Ctrl+Shift+B` (or `prefix B`) hides or shows the sidebar in every window. `Alt+s` focuses it (and shows it).
- `Ctrl+Shift+O` splits right, `Ctrl+Shift+E` splits below. They do nothing in the sidebar.
- `Alt+arrows` moves between panes. `Alt+z` zooms.
- `prefix O`, `prefix E`, `prefix N`, `prefix +` and `prefix B` do the same as the `Ctrl+Shift` keys, in any terminal.
- `prefix ?` opens the help view (same as `?` in the sidebar), even with the sidebar hidden. `prefix Tab` switches to the last session. `prefix /` shows the tmux key list.
- Status line (top): session pill and window tabs on the left; on the right, the agent counters `◉ n ⠹ n ✓ n ◌ n ✕ n` (zeros hidden), the git branch `⎇` of the current pane and the time. `aif-agents status <dir>` renders the counters and the branch; the agent hook refreshes the line on each event. Colors follow the palette of the sidebar (accent `#BB9AF7`).
- Mouse selection copies to the system clipboard and shows "Copied to clipboard": OSC 52 to the terminal, plus `aif-platform copy` (Wayland clipboard) on native Linux. Right click pastes (outside the sidebar).

Agent bell:

- Claude Code rings the terminal bell when it waits or finishes (`preferredNotifChannel: "terminal_bell"` in `.claude/settings.json`).
- tmux sends a bell only to clients of the session that rang. `config/tmux-bell-relay.sh` (`alert-bell` hook) forwards the bell of a background session to every attached client.
- Windows Terminal: `"bellStyle": "taskbar"` on the WSL profiles flashes the taskbar icon.

Save and restore ([tmux-resurrect](https://github.com/tmux-plugins/tmux-resurrect) + [tmux-continuum](https://github.com/tmux-plugins/tmux-continuum)):

- The layout is saved every 15 min (`prefix Ctrl-s` saves now). It is restored when the tmux server starts (`prefix Ctrl-r` restores now).
- tmux restores sessions, windows, panes and folders. Processes are not kept: start each agent again (`claude -c` resumes the last conversation of the folder).
- continuum neither saves nor restores while another tmux server runs (`tmux -L …`).
- `config/tmux-resurrect-sidebar.sh` keeps the sidebar out of the save file. After a restore, `config/tmux-sidebar.sh` opens it again.

Agent state (read by the views; one file per agent):

- Claude Code hooks call `bin/aif-agent-hook` (template `.claude/settings.json.tpl`, merged by `install.sh`). It writes `$XDG_RUNTIME_DIR/aif/agents/<pane>.json`: `state` (`running`, `check`, `done`, `error`), task, question and options, `ask` (`tool`, `permission`, `prose`), last tool, subagents, model and context. Each entry into and exit from `check` adds one line to `~/.claude/logs/aif-check.log` (`$AIF_CHECK_LOG`). It does nothing outside tmux and always exits 0 (about 35–50 ms per event on WSL, one jq call).
- `check` means the agent waits for you: a permission prompt, a question (`AskUserQuestion`), or a question left in prose (the last line of the last message ends with `?`, outside a code block or a URL; `ask` is `prose`, `tool` or `permission`; `scripts/replay-prose-questions.py` measures the rule on past transcripts). On entry into `check`, a system notification goes out through `aif-platform notify` when the pane is not visible. `AIF_NOTIFY_DONE=1` also notifies the end of a turn.
- `bin/aif-statusline` is the Claude Code `statusLine`: it records the model and the context use, then runs the previous `statusLine` command (`install.sh` chains it, it does not replace it).
- `aif-agents list --json` is the only data source of the views. It adds the tmux session, a `jump` number (1–9, display order) and git stats (`git diff --numstat HEAD`, cached 5 s). It computes `stale` (no event for `AIF_STALE_AFTER` seconds, default 3600, except `check`), `unknown` (a `claude` process in a pane without a state file) and `error` (a state file but no `claude` process left in the pane).

Agents sidebar (`aif-sidebar`, Rust + ratatui, `sidebar/`; decision: [`docs/adr/0001-agents-sidebar.md`](adr/0001-agents-sidebar.md)):

- `install.sh` builds it with `cargo` (Rust 1.85+; Ubuntu 26.04: `sudo apt install cargo`) and links `~/.local/bin/aif-sidebar`. It reads only `aif-agents` and tmux. A running sidebar restarts itself on a rebuilt binary within a second.
- `config/tmux-sidebar.sh` keeps one sidebar pane (pane option `@aif_sidebar`, 44 columns, `@aif-sidebar-width`) on the left of each window while the sidebar is on (`@aif-sidebar`). tmux hooks open it on attach, on a session or window change and in a new window. A lock (`tmux wait-for`) prevents a second one.
- Tabs `SESSIONS`, `AGENTS`, `ACTIONS` (`Tab` switches); the ai-dotfiles version is top right. `Ctrl+C` closes the sidebar of the window until the next window change.
- Mouse and keyboard do the same things. One click acts like `⏎`, on the whole row. Each key shown in the footer, and the filter and sort of the AGENTS header, is a button that sends its key.
- SESSIONS: `+ Terminal`, `+ New session` and `+ New project` on top, then the tree session → agents → subagents, with the count of agents per state. The current session has `▸`. `↑↓` move, `⏎` switch, `r` rename, `T` new terminal, `N` new, `+` new project, `K` kill.
- ACTIONS: the target session (the SESSIONS cursor), then the actions: new terminal, new session, new project, rename, last session, kill, split right / below, zoom, save now (with the time of the last save), save & exit, exit (detach), restore the last save, hide the sidebar. `⏎` runs the selected action; `r`, `s`, `d` run directly. Pane actions act on the last active pane, not on the sidebar.
- Confirmation screens (New session, New project, Kill session, Save & exit, Rename) dim the working pane. `Esc` or `[ Cancel ]` cancels.
- Help: the `?` box of the tab bar, `? help` in the footer, the `?` key and `prefix ?` open the same centered popup (`aif-sidebar help`): keys in four columns (NAVIGATE, AGENTS, SESSIONS, PANES & VIEW; two or one on a narrow terminal) and the glyph legend. `Esc` closes it.
- AGENTS groups agents by priority: TO CHECK, ERROR, DONE, RUNNING, UNKNOWN, STALE. Keys: `↑↓`/`j k` move, `/` filter, `o` sort (priority, session, recent), `⏎` go to the agent, `p` peek, `x` interrupt a running agent.
- An agent in TO CHECK shows its question and buttons `[1 …] [2 …] [i Reply…]`. `1`–`3` (or a click) sends that answer to the agent pane (`tmux send-keys`); `i` opens a reply field. Otherwise `1`–`9` jumps to the agent with that number.
- Keys checked in Claude Code 2.1.318: a question takes the option digit; a free reply takes the "Type something" digit, the text and Enter. A permission takes `1` (Yes) or `2` (Always). **No** sends `Escape`, never `3`: the menu has 3 or 4 options, and option 3 can be "switch to auto mode". A free reply to a permission sends `Escape`, then the text as a prompt.
- A refusal fires no Claude Code hook: the sidebar shows the agent as done until its next event.
- Peek (`p`): a popup on the right (40 %) with the agent output (`Output`) and its diff against HEAD (`Diff`, `Tab` switches). `⏎` goes to the agent, `Esc` closes.

First install: in tmux, press `prefix I` to install tmux-resurrect and tmux-continuum. `install.sh` builds `aif-sidebar` with `cargo`; without Rust 1.85+, it prints how to install it and tmux keeps working without the sidebar (`Ctrl+Shift+K` and `prefix Q` fall back to a `y/n` prompt).

Windows Terminal (manual step, `settings.json`):

- `ctrl+shift+m`: `newTab` action with `"commandline": "wsl.exe -d Ubuntu --cd ~ -- zsh -lic tma"`. It overrides the default mark-mode key.
- `ctrl+shift+o`: `sendInput` `"\u001b[[tma-o"`. tmux maps it to a split on the right (`user-keys[0]`).
- `ctrl+shift+e`: `sendInput` `"\u001b[[tma-e"`. tmux maps it to a split below (`user-keys[1]`).
- `ctrl+shift+x`: `sendInput` `"\u001b[[tma-x"` (`user-keys[2]`, close pane).
- `ctrl+shift+n`: `sendInput` `"\u001b[[tma-n"` (`user-keys[3]`, new session). It overrides the default new-window key.
- `ctrl+shift+b`: `sendInput` `"\u001b[[tma-b"` (`user-keys[4]`, show / hide the sidebar).
- `ctrl+shift+k`: `sendInput` `"\u001b[[tma-k"` (`user-keys[5]`, kill session).
- These keys send text in every Windows Terminal tab, also outside tmux.
- `"bellStyle": "taskbar"` on each WSL profile.

Ghostty: `config/ghostty/config` (linked by `install.sh`) sends `Ctrl+Shift+O/E/N/X/B/K` as CSI u extended keys instead of the Ghostty actions, and tmux binds `C-S-o`, `C-S-e`, `C-S-x`, `C-S-n`, `C-S-b` and `C-S-k`. Ghostty reads its config at start: after `install.sh`, press `Ctrl+Shift+,` to reload it. Without the reload, `Ctrl+Shift+O/E` open a Ghostty split, which runs a second tmux view with its own sidebar.

Tests (bats, dedicated tmux server `tmux -L aif-test`):

- `npx --yes bats@1.13.0 tests/` checks that the config loads with the local tmux on both platforms, replays a tmux-resurrect restore, and drives the sidebar end to end (one sidebar for the server, screens, answers). Rust tests: `cd sidebar && cargo test`.
- `cd sidebar && cargo test --test e2e` runs the mouse tests, in the style of Playwright. A real tmux client runs in an emulated terminal ([tui-test](https://github.com/microsoft/tui-test)). The tests click and type like a user, then read the tmux state. Each test uses its own `HOME` and `TMUX_TMPDIR` under `/tmp`, without `TMUX`, so it never reaches your sessions.
- `tests/container.sh [image] [wsl|linux]` runs `install.sh` twice in a clean container, then the bats tests with the tmux of the image. Example: `tests/container.sh ubuntu:26.04 linux`.
