//! aif-sidebar — vue sessions / agents tmux d'ai-dotfiles.
//!   aif-sidebar              la sidebar (onglets SESSIONS, AGENTS, ACTIONS)
//!   aif-sidebar peek <pane>  l'aperçu d'un agent (lancé dans un popup tmux)
//!   aif-sidebar help         la vue d'aide (popup tmux)
//!   aif-sidebar --version
//! Données : `aif-agents` (état des agents) et tmux, rien d'autre.

mod app;
mod help;
mod model;
mod peek;
mod sessions;
mod theme;
mod tmux;
mod ui;

use std::io::stdout;
use std::sync::mpsc;
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use anyhow::{Context, Result};
use ratatui::crossterm::event::{
    self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode, KeyEventKind, KeyModifiers,
    MouseButton, MouseEventKind,
};
use ratatui::crossterm::execute;
use ratatui::layout::{Position, Rect};

use app::{App, Effect, Key};
use peek::{Peek, PeekEffect};
use ui::Hit;

const REFRESH: Duration = Duration::from_secs(1);
const TICK: Duration = Duration::from_millis(100);

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match args.first().map(String::as_str) {
        None => run_sidebar(),
        Some("help") => run_help(),
        Some("peek") => run_peek(
            args.get(1)
                .context("usage: aif-sidebar peek <pane>")?
                .clone(),
        ),
        Some("--version") => {
            println!(
                "aif-sidebar {} (ai-dotfiles {})",
                env!("CARGO_PKG_VERSION"),
                dotfiles_version()
            );
            Ok(())
        }
        Some(a) => {
            anyhow::bail!("unknown argument {a}. Usage: aif-sidebar [peek <pane>] [--version]")
        }
    }
}

fn now() -> i64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |d| d.as_secs() as i64)
}

/// Version d'ai-dotfiles : dernier tag git du dépôt (AIF_DOTFILES, sinon ~/ai-dotfiles).
fn dotfiles_version() -> String {
    let repo = std::env::var("AIF_DOTFILES")
        .unwrap_or_else(|_| format!("{}/ai-dotfiles", std::env::var("HOME").unwrap_or_default()));
    std::process::Command::new("git")
        .args(["-C", &repo, "describe", "--tags", "--abbrev=0"])
        .output()
        .ok()
        .filter(|o| o.status.success())
        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
        .unwrap_or_else(|| "dev".into())
}

fn to_key(code: KeyCode, mods: KeyModifiers) -> Option<Key> {
    Some(match code {
        KeyCode::Char('c') if mods.contains(KeyModifiers::CONTROL) => Key::Quit,
        KeyCode::Char(c) => Key::Char(c),
        KeyCode::Up => Key::Up,
        KeyCode::Down => Key::Down,
        KeyCode::Enter => Key::Enter,
        KeyCode::Esc => Key::Esc,
        KeyCode::Tab => Key::Tab,
        KeyCode::BackTab => Key::BackTab,
        KeyCode::Backspace => Key::Backspace,
        _ => return None,
    })
}

fn hit_at<H: Clone>(hits: &[(Rect, H)], x: u16, y: u16) -> Option<H> {
    hits.iter()
        .find(|(r, _)| r.contains(Position { x, y }))
        .map(|(_, h)| h.clone())
}

/// Terminal plein écran avec souris ; restauré même en cas de panique (ratatui::init).
fn with_terminal<T>(f: impl FnOnce(&mut ratatui::DefaultTerminal) -> Result<T>) -> Result<T> {
    let mut term = ratatui::init();
    execute!(stdout(), EnableMouseCapture).ok();
    let out = f(&mut term);
    execute!(stdout(), DisableMouseCapture).ok();
    ratatui::restore();
    out
}

/// Données lues à chaque rafraîchissement, hors de la boucle d'affichage (≈ 50 ms).
struct Snapshot {
    agents: Result<Vec<model::Agent>, String>,
    sessions: Vec<sessions::Session>,
    current: String,
    last_save: Option<i64>,
}

fn run_sidebar() -> Result<()> {
    let (tx, rx) = mpsc::channel();
    thread::spawn(move || {
        loop {
            let snap = Snapshot {
                agents: model::load_agents().map_err(|e| e.to_string()),
                sessions: sessions::load_sessions(),
                current: sessions::current_session(),
                last_save: sessions::last_save(),
            };
            if tx.send(snap).is_err() {
                break;
            }
            thread::sleep(REFRESH);
        }
    });
    let mut app = App::new(dotfiles_version());
    app.home = sessions::home();
    let mut dimmed = false;
    let restart = with_terminal(|term| {
        let mut last_tick = Instant::now();
        loop {
            app.now = now();
            while let Ok(snap) = rx.try_recv() {
                // Binaire remplacé (cargo build, install.sh) : relancer le nouveau, sinon la
                // sidebar garde l'ancien code et ne trouve plus son exécutable (aide, aperçu)
                if replaced() {
                    tmux::dim(false);
                    return Ok(true);
                }
                match snap.agents {
                    Ok(agents) => {
                        app.load_error = None;
                        app.set_agents(agents);
                    }
                    Err(e) => app.load_error = Some(e),
                }
                app.set_sessions(snap.sessions, snap.current);
                app.last_save = snap.last_save;
            }
            // Écran de confirmation ouvert : pane de travail atténué
            if app.screen.is_some() != dimmed {
                dimmed = app.screen.is_some();
                tmux::dim(dimmed);
            }
            let mut hits = vec![];
            term.draw(|f| hits = ui::draw(f, &mut app))?;
            if event::poll(TICK.saturating_sub(last_tick.elapsed()))? {
                let ev = event::read()?;
                // La sidebar vient peut-être de changer de session (join-pane) : la session
                // courante doit être juste avant la touche (Ctrl+Shift+K) ou le clic.
                if matches!(ev, Event::Key(_))
                    || matches!(ev, Event::Mouse(m) if matches!(m.kind, MouseEventKind::Down(_)))
                {
                    let cur = sessions::current_session();
                    if cur != app.current {
                        app.set_sessions(app.sessions.clone(), cur);
                    }
                }
                let effect = match ev {
                    Event::Key(k) if k.kind == KeyEventKind::Press => {
                        to_key(k.code, k.modifiers).map_or(Effect::None, |k| app.key(k))
                    }
                    Event::Mouse(m) => match m.kind {
                        MouseEventKind::Down(MouseButton::Left) => {
                            click(&mut app, hit_at(&hits, m.column, m.row))
                        }
                        MouseEventKind::ScrollDown => app.key(Key::Down),
                        MouseEventKind::ScrollUp => app.key(Key::Up),
                        _ => Effect::None,
                    },
                    _ => Effect::None,
                };
                if effect == Effect::Quit {
                    tmux::dim(false);
                    return Ok(false);
                }
                if matches!(effect, Effect::OpenNew | Effect::OpenProject) {
                    let folders = sessions::folders(&app.home);
                    app.open_new(folders, effect == Effect::OpenProject);
                }
                if let Err(e) = apply(&app, &effect) {
                    app.message = Some(e.to_string());
                } else if let Effect::Answer { pane, .. } = &effect {
                    let sent = app.answered.get(pane).map(|a| a.text.clone());
                    app.message = Some(format!("sent: {}", sent.unwrap_or_default()));
                }
            }
            if last_tick.elapsed() >= TICK {
                app.tick += 1;
                last_tick = Instant::now();
            }
        }
    })?;
    if restart {
        use std::os::unix::process::CommandExt;
        // exec garde le PID et le pane : le nouveau binaire prend la place
        return Err(std::process::Command::new(tmux::self_path()).exec().into());
    }
    Ok(())
}

/// Le noyau suffixe « (deleted) » au lien de l'exécutable quand le fichier a été remplacé.
fn replaced() -> bool {
    std::fs::read_link("/proc/self/exe").is_ok_and(|p| p.to_string_lossy().ends_with(" (deleted)"))
}

fn click(app: &mut App, hit: Option<Hit>) -> Effect {
    match hit {
        Some(Hit::Tab(t)) => app.set_tab(t),
        Some(Hit::Help) => return Effect::Help,
        Some(Hit::Key(k)) => return app.key(k),
        Some(Hit::Agent(i)) => {
            app.select(i);
            if let Some(a) = app.selected_agent() {
                return Effect::GoTo(a.pane.clone());
            }
        }
        Some(Hit::Answer(pane, n)) => return app.click_answer(&pane, n),
        Some(Hit::Session(i)) => {
            app.session_sel = i;
            if let Some(s) = app.sessions.get(i) {
                return Effect::Switch(s.name.clone());
            }
        }
        Some(Hit::Action(i)) => return app.click_action(i),
        Some(Hit::Folder(i)) => return app.click_folder(i),
        Some(Hit::Reply(pane)) => {
            if let Some(i) = app.visible().iter().position(|a| a.pane == pane) {
                app.select(i);
                app.start_reply();
            }
        }
        None => {}
    }
    Effect::None
}

/// Exécute l'effet d'une touche ou d'un clic (tmux).
fn apply(app: &App, e: &Effect) -> Result<()> {
    match e {
        Effect::None | Effect::Quit | Effect::OpenNew | Effect::OpenProject => Ok(()),
        Effect::Switch(n) => tmux::switch(n),
        Effect::Create { name, dir } => tmux::create(name, dir),
        Effect::KillSession(n) => tmux::kill_session(n),
        Effect::SaveExit => tmux::save_exit(),
        Effect::Detach => tmux::detach(),
        Effect::Save => tmux::save(),
        Effect::Restore => tmux::restore(),
        Effect::Rename { from, to } => tmux::rename(from, to),
        Effect::SplitRight => tmux::split(true),
        Effect::SplitBelow => tmux::split(false),
        Effect::Zoom => tmux::zoom(),
        Effect::ToggleSidebar => tmux::toggle_sidebar(),
        Effect::LastSession => tmux::last_session(),
        Effect::Help => tmux::open_help(),
        Effect::GoTo(p) => tmux::go_to(p),
        Effect::Peek(p) => tmux::open_peek(p),
        Effect::Interrupt(p) => tmux::interrupt(p),
        Effect::Answer { pane, choice, text } => {
            let agent = app
                .agents
                .iter()
                .find(|a| &a.pane == pane)
                .context("agent gone")?;
            tmux::send(pane, &tmux::answer_keys(agent, *choice, text.as_deref()))
        }
    }
}

/// Vue d'aide, lancée dans un popup tmux (`prefix ?`, touche « ? » de la sidebar).
fn run_help() -> Result<()> {
    with_terminal(|term| {
        loop {
            term.draw(help::draw)?;
            match event::read()? {
                Event::Key(k) if k.kind == KeyEventKind::Press => {
                    if matches!(
                        k.code,
                        KeyCode::Esc | KeyCode::Char('q') | KeyCode::Char('?') | KeyCode::Enter
                    ) || (k.code == KeyCode::Char('c')
                        && k.modifiers.contains(KeyModifiers::CONTROL))
                    {
                        return Ok(());
                    }
                }
                Event::Mouse(m) if matches!(m.kind, MouseEventKind::Down(_)) => return Ok(()),
                _ => {}
            }
        }
    })
}

fn run_peek(pane: String) -> Result<()> {
    let mut p = Peek::new(pane);
    let mut last = Instant::now() - REFRESH;
    with_terminal(|term| {
        loop {
            if last.elapsed() >= REFRESH {
                last = Instant::now();
                p.agent = model::load_agents()
                    .ok()
                    .and_then(|v| v.into_iter().find(|a| a.pane == p.pane));
                p.error = None;
                match tmux::capture(&p.pane, 500) {
                    Ok(o) => p.output = o,
                    Err(e) => p.error = Some(e.to_string()),
                }
                p.diff = model::load_diff(&p.pane).ok();
                p.tick += 1;
            }
            let mut hits = vec![];
            term.draw(|f| hits = peek::draw(f, &p))?;
            if event::poll(TICK)? {
                let effect = match event::read()? {
                    Event::Key(k) if k.kind == KeyEventKind::Press => {
                        to_key(k.code, k.modifiers).map_or(PeekEffect::None, |k| p.key(k))
                    }
                    Event::Mouse(m)
                        if matches!(m.kind, MouseEventKind::Down(MouseButton::Left)) =>
                    {
                        hit_at(&hits, m.column, m.row).map_or(PeekEffect::None, |h| p.click(&h))
                    }
                    _ => PeekEffect::None,
                };
                match effect {
                    PeekEffect::None => {}
                    PeekEffect::Close => return Ok(()),
                    PeekEffect::GoTo(pane) => {
                        tmux::go_to(&pane)?;
                        return Ok(());
                    }
                }
            }
        }
    })
}
