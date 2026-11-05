//! État de la sidebar et touches. Aucun effet de bord ici : chaque touche rend un `Effect`
//! que `main` exécute (tmux), ce qui garde ce module testable.

use std::collections::HashMap;

use crate::model::Agent;
use crate::sessions::{Fit, Session, fit, tilde};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Tab {
    Sessions,
    Agents,
    Actions,
}

impl Tab {
    pub const ALL: [Tab; 3] = [Tab::Sessions, Tab::Agents, Tab::Actions];
    fn next(self) -> Tab {
        Tab::ALL[(Tab::ALL.iter().position(|t| *t == self).unwrap() + 1) % 3]
    }
    fn prev(self) -> Tab {
        Tab::ALL[(Tab::ALL.iter().position(|t| *t == self).unwrap() + 2) % 3]
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Sort {
    Priority,
    Session,
    Recent,
}

impl Sort {
    pub fn label(self) -> &'static str {
        match self {
            Sort::Priority => "priority",
            Sort::Session => "session",
            Sort::Recent => "recent",
        }
    }
    fn next(self) -> Sort {
        match self {
            Sort::Priority => Sort::Session,
            Sort::Session => Sort::Recent,
            Sort::Recent => Sort::Priority,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    Normal,
    Filter,
    Reply,
}

/// Touche reçue, indépendante de crossterm.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Key {
    Char(char),
    Up,
    Down,
    Enter,
    Esc,
    Tab,
    BackTab,
    Backspace,
    /// Ctrl+C : quitte la sidebar
    Quit,
}

/// Ce que `main` doit faire après une touche ou un clic.
#[derive(Debug, Clone, PartialEq)]
pub enum Effect {
    None,
    Quit,
    GoTo(String),
    Peek(String),
    /// Réponse à un agent en attente : choix numéroté ou texte libre.
    Answer {
        pane: String,
        choice: Option<usize>,
        text: Option<String>,
    },
    Interrupt(String),
    /// Ouvre l'écran New session : `main` lit les dossiers, puis appelle `open_new`.
    OpenNew,
    Switch(String),
    Create {
        name: String,
        dir: String,
    },
    /// Sauvegarde, puis tue la session
    KillSession(String),
    /// Sauvegarde toutes les sessions, puis quitte tmux
    SaveExit,
    Detach,
    Save,
    Restore,
    Rename {
        from: String,
        to: String,
    },
    SplitRight,
    SplitBelow,
    Zoom,
    ToggleSidebar,
    LastSession,
    /// Vue d'aide (popup tmux)
    Help,
}

/// Écran de confirmation affiché dans la sidebar (le pane courant est atténué).
#[derive(Debug, Clone, PartialEq)]
pub enum Screen {
    New {
        filter: String,
        folders: Vec<String>,
        sel: usize,
    },
    Kill(String),
    SaveExit,
    Rename {
        session: String,
        input: String,
    },
}

/// Bouton d'un écran (clic).
#[derive(Debug, Clone, PartialEq)]
pub enum Button {
    Cancel,
    Confirm,
    ExitOnly,
    Folder(usize),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ActionKind {
    New,
    Rename,
    Last,
    Kill,
    SplitRight,
    SplitBelow,
    Zoom,
    Save,
    SaveExit,
    Exit,
    Restore,
    Hide,
}

/// Ligne de l'onglet ACTIONS.
pub struct Action {
    pub group: &'static str,
    pub icon: &'static str,
    pub label: &'static str,
    pub keys: &'static str,
    pub note: &'static str,
    pub kind: ActionKind,
}

pub const ACTIONS: [Action; 12] = [
    Action {
        group: "SESSION",
        icon: "+",
        label: "New session…",
        keys: "⌃⇧N",
        note: "pick a folder, name comes from it",
        kind: ActionKind::New,
    },
    Action {
        group: "SESSION",
        icon: "✎",
        label: "Rename",
        keys: "r",
        note: "",
        kind: ActionKind::Rename,
    },
    Action {
        group: "SESSION",
        icon: "⇄",
        label: "Switch to last session",
        keys: "prefix ⇥",
        note: "",
        kind: ActionKind::Last,
    },
    Action {
        group: "SESSION",
        icon: "✕",
        label: "Kill session…",
        keys: "⌃⇧K",
        note: "",
        kind: ActionKind::Kill,
    },
    Action {
        group: "PANES",
        icon: "┃",
        label: "Split right",
        keys: "⌃⇧O",
        note: "",
        kind: ActionKind::SplitRight,
    },
    Action {
        group: "PANES",
        icon: "━",
        label: "Split below",
        keys: "⌃⇧E",
        note: "",
        kind: ActionKind::SplitBelow,
    },
    Action {
        group: "PANES",
        icon: "⤢",
        label: "Zoom pane",
        keys: "⌥Z",
        note: "",
        kind: ActionKind::Zoom,
    },
    Action {
        group: "SAVE & EXIT",
        icon: "↓",
        label: "Save now",
        keys: "s",
        note: "",
        kind: ActionKind::Save,
    },
    Action {
        group: "SAVE & EXIT",
        icon: "⇣",
        label: "Save & exit…",
        keys: "prefix Q",
        note: "save every session, then quit tmux",
        kind: ActionKind::SaveExit,
    },
    Action {
        group: "SAVE & EXIT",
        icon: "→",
        label: "Exit",
        keys: "d",
        note: "detach: sessions and agents keep running",
        kind: ActionKind::Exit,
    },
    Action {
        group: "SAVE & EXIT",
        icon: "↺",
        label: "Restore last save",
        keys: "",
        note: "",
        kind: ActionKind::Restore,
    },
    Action {
        group: "VIEW",
        icon: "◧",
        label: "Hide sidebar",
        keys: "⌃⇧B",
        note: "",
        kind: ActionKind::Hide,
    },
];

/// Réponse envoyée, gardée tant que le fichier d'état de l'agent n'a pas changé (même
/// `updated_at`) : un refus (Échap) ne déclenche aucun hook, l'état resterait « check ».
#[derive(Debug, Clone)]
pub struct Answered {
    pub text: String,
    /// `updated_at` de l'agent au moment de la réponse
    pub seen: Option<i64>,
    /// État affiché en attendant le prochain événement : running, ou done après un refus
    pub shown: &'static str,
}

pub struct App {
    pub tab: Tab,
    pub agents: Vec<Agent>,
    pub selected: usize,
    pub filter: String,
    pub input: String,
    pub mode: Mode,
    pub sort: Sort,
    pub answered: HashMap<String, Answered>,
    pub message: Option<String>,
    pub load_error: Option<String>,
    pub version: String,
    pub tick: usize,
    pub now: i64,
    /// Onglets abrégés quand la sidebar est étroite (calculé au rendu).
    pub short_tabs: bool,
    pub sessions: Vec<Session>,
    /// Session de la sidebar (session courante)
    pub current: String,
    pub home: String,
    /// Curseur des onglets SESSIONS et ACTIONS (session cible)
    pub session_sel: usize,
    pub action_sel: usize,
    pub screen: Option<Screen>,
    pub last_save: Option<i64>,
}

impl App {
    pub fn new(version: String) -> App {
        App {
            tab: Tab::Agents,
            agents: vec![],
            selected: 0,
            filter: String::new(),
            input: String::new(),
            mode: Mode::Normal,
            sort: Sort::Priority,
            answered: HashMap::new(),
            message: None,
            load_error: None,
            version,
            tick: 0,
            now: 0,
            short_tabs: false,
            sessions: vec![],
            current: String::new(),
            home: String::new(),
            session_sel: 0,
            action_sel: 0,
            screen: None,
            last_save: None,
        }
    }

    /// Nouvelles sessions tmux : le curseur reste sur la même session, sinon va sur la courante.
    pub fn set_sessions(&mut self, sessions: Vec<Session>, current: String) {
        let keep = self
            .sessions
            .get(self.session_sel)
            .map(|s| s.name.clone())
            .filter(|_| !self.sessions.is_empty());
        self.sessions = sessions;
        let want = keep.unwrap_or_else(|| current.clone());
        self.session_sel = self
            .sessions
            .iter()
            .position(|s| s.name == want)
            .unwrap_or(0);
        self.current = current;
    }

    /// Session visée par SESSIONS et ACTIONS : celle sous le curseur.
    pub fn target(&self) -> Option<&Session> {
        self.sessions.get(self.session_sel)
    }

    pub fn agents_of(&self, session: &str) -> Vec<&Agent> {
        self.agents
            .iter()
            .filter(|a| a.session == session)
            .collect()
    }

    pub fn open_new(&mut self, folders: Vec<String>) {
        self.screen = Some(Screen::New {
            filter: String::new(),
            folders,
            sel: 0,
        });
    }

    /// Dossiers de l'écran New session après le filtre.
    pub fn new_folders(&self) -> Vec<&String> {
        match &self.screen {
            Some(Screen::New {
                filter, folders, ..
            }) => {
                let f = filter.to_lowercase();
                folders
                    .iter()
                    .filter(|d| tilde(d, &self.home).to_lowercase().contains(&f))
                    .collect()
            }
            _ => vec![],
        }
    }

    pub fn fit_of(&self, dir: &str) -> Fit {
        fit(dir, &self.home, &self.sessions)
    }

    fn run_action(&mut self, kind: ActionKind) -> Effect {
        let target = self.target().map(|s| s.name.clone());
        match kind {
            ActionKind::New => return Effect::OpenNew,
            ActionKind::Rename => {
                if let Some(t) = target {
                    self.screen = Some(Screen::Rename {
                        session: t.clone(),
                        input: t,
                    });
                }
            }
            ActionKind::Last => return Effect::LastSession,
            ActionKind::Kill => {
                if let Some(t) = target {
                    self.screen = Some(Screen::Kill(t));
                }
            }
            ActionKind::SplitRight => return Effect::SplitRight,
            ActionKind::SplitBelow => return Effect::SplitBelow,
            ActionKind::Zoom => return Effect::Zoom,
            ActionKind::Save => return Effect::Save,
            ActionKind::SaveExit => self.screen = Some(Screen::SaveExit),
            ActionKind::Exit => return Effect::Detach,
            ActionKind::Restore => return Effect::Restore,
            ActionKind::Hide => return Effect::ToggleSidebar,
        }
        Effect::None
    }

    pub fn click_action(&mut self, i: usize) -> Effect {
        self.action_sel = i.min(ACTIONS.len() - 1);
        self.run_action(ACTIONS[self.action_sel].kind)
    }

    pub fn click_button(&mut self, b: Button) -> Effect {
        match b {
            Button::Cancel => self.key_screen(Key::Esc),
            Button::Confirm => self.key_screen(Key::Enter),
            Button::ExitOnly => self.key_screen(Key::Char('d')),
            Button::Folder(i) => {
                if let Some(Screen::New { sel, .. }) = &mut self.screen {
                    *sel = i;
                }
                Effect::None
            }
        }
    }

    fn key_screen(&mut self, k: Key) -> Effect {
        let Some(screen) = self.screen.clone() else {
            return Effect::None;
        };
        let close = |app: &mut App, e: Effect| {
            app.screen = None;
            e
        };
        match (screen, k) {
            (_, Key::Esc) => close(self, Effect::None),
            (Screen::New { .. }, Key::Enter) => {
                let Some(dir) = self
                    .new_folders()
                    .get(self.new_sel())
                    .map(|d| d.to_string())
                else {
                    return Effect::None;
                };
                let e = match self.fit_of(&dir) {
                    Fit::Attach(n) => Effect::Switch(n),
                    f => Effect::Create {
                        name: f.name().to_string(),
                        dir,
                    },
                };
                close(self, e)
            }
            (Screen::New { .. }, k) => {
                let n = self.new_folders().len();
                if let Some(Screen::New { filter, sel, .. }) = &mut self.screen {
                    match k {
                        Key::Up => *sel = sel.saturating_sub(1),
                        Key::Down => *sel = (*sel + 1).min(n.saturating_sub(1)),
                        Key::Char(c) => {
                            filter.push(c);
                            *sel = 0;
                        }
                        Key::Backspace => {
                            filter.pop();
                            *sel = 0;
                        }
                        _ => {}
                    }
                }
                Effect::None
            }
            (Screen::Kill(s), Key::Enter | Key::Char('y')) => close(self, Effect::KillSession(s)),
            (Screen::Kill(_), Key::Char('n')) => close(self, Effect::None),
            (Screen::SaveExit, Key::Enter | Key::Char('y')) => close(self, Effect::SaveExit),
            (Screen::SaveExit, Key::Char('d')) => close(self, Effect::Detach),
            (Screen::SaveExit, Key::Char('n')) => close(self, Effect::None),
            (Screen::Rename { session, input }, Key::Enter) => {
                let to = input.trim().to_string();
                let e = if to.is_empty() || to == session {
                    Effect::None
                } else {
                    Effect::Rename { from: session, to }
                };
                close(self, e)
            }
            (Screen::Rename { .. }, k) => {
                if let Some(Screen::Rename { input, .. }) = &mut self.screen {
                    match k {
                        Key::Char(c) => input.push(c),
                        Key::Backspace => {
                            input.pop();
                        }
                        _ => {}
                    }
                }
                Effect::None
            }
            _ => Effect::None,
        }
    }

    pub fn new_sel(&self) -> usize {
        match &self.screen {
            Some(Screen::New { sel, .. }) => *sel,
            _ => 0,
        }
    }

    /// Nouvelle liste d'agents (rafraîchissement) : garde la sélection sur le même pane.
    pub fn set_agents(&mut self, agents: Vec<Agent>) {
        let keep = self.selected_agent().map(|a| a.pane.clone());
        self.agents = agents;
        // Garder la réponse tant qu'aucun nouvel événement n'est arrivé, ou tant que l'agent tourne
        // (note « you answered »).
        let agents = &self.agents;
        self.answered.retain(|pane, ans| {
            agents
                .iter()
                .find(|a| &a.pane == pane)
                .is_some_and(|a| a.updated_at == ans.seen || a.state == "running")
        });
        if let Some(pane) = keep
            && let Some(i) = self.visible().iter().position(|a| a.pane == pane)
        {
            self.selected = i;
        }
        self.clamp();
    }

    /// État affiché : après une réponse et avant le prochain événement, l'état attendu
    /// (running, ou done après un refus) au lieu du « check » encore écrit dans le fichier.
    pub fn shown_state<'a>(&self, a: &'a Agent) -> &'a str {
        match self.answered.get(&a.pane) {
            Some(ans) if a.updated_at == ans.seen => ans.shown,
            _ => &a.state,
        }
    }

    /// Agents filtrés et triés, dans l'ordre affiché.
    pub fn visible(&self) -> Vec<&Agent> {
        let needle = self.filter.to_lowercase();
        let mut v: Vec<&Agent> = self
            .agents
            .iter()
            .filter(|a| needle.is_empty() || a.haystack().contains(&needle))
            .collect();
        match self.sort {
            // aif-agents rend déjà l'ordre de priorité ; un agent répondu passe chez les running.
            Sort::Priority => v.sort_by_key(|a| rank(self.shown_state(a))),
            Sort::Session => v.sort_by(|a, b| {
                a.session
                    .cmp(&b.session)
                    .then(pane_num(&a.pane).cmp(&pane_num(&b.pane)))
            }),
            Sort::Recent => v.sort_by_key(|a| std::cmp::Reverse(a.updated_at.unwrap_or(0))),
        }
        v
    }

    pub fn selected_agent(&self) -> Option<&Agent> {
        self.visible().get(self.selected).copied()
    }

    fn clamp(&mut self) {
        let n = self.visible().len();
        self.selected = if n == 0 { 0 } else { self.selected.min(n - 1) };
    }

    pub fn select(&mut self, i: usize) {
        self.selected = i;
        self.clamp();
    }

    pub fn set_tab(&mut self, t: Tab) {
        self.tab = t;
        self.mode = Mode::Normal;
    }

    pub fn key(&mut self, k: Key) -> Effect {
        self.message = None;
        if k == Key::Quit {
            return Effect::Quit;
        }
        if self.screen.is_some() {
            return self.key_screen(k);
        }
        match self.mode {
            Mode::Filter => return self.key_filter(k),
            Mode::Reply => return self.key_reply(k),
            Mode::Normal => {}
        }
        match k {
            Key::Tab => self.set_tab(self.tab.next()),
            Key::BackTab => self.set_tab(self.tab.prev()),
            Key::Char('?') => return Effect::Help,
            // Écrans, depuis n'importe quel onglet (Ctrl+Shift+N / K, prefix Q les envoient)
            Key::Char('N') => return Effect::OpenNew,
            Key::Char('K') => return self.run_action(ActionKind::Kill),
            Key::Char('Q') => return self.run_action(ActionKind::SaveExit),
            _ if self.tab == Tab::Sessions => return self.key_sessions(k),
            _ if self.tab == Tab::Actions => return self.key_actions(k),
            Key::Up | Key::Char('k') => self.selected = self.selected.saturating_sub(1),
            Key::Down | Key::Char('j') => self.select(self.selected + 1),
            Key::Char('/') => self.mode = Mode::Filter,
            Key::Char('o') => {
                self.sort = self.sort.next();
                self.clamp();
            }
            Key::Enter => {
                return self
                    .selected_agent()
                    .map_or(Effect::None, |a| Effect::GoTo(a.pane.clone()));
            }
            Key::Char('p') => {
                return self
                    .selected_agent()
                    .map_or(Effect::None, |a| Effect::Peek(a.pane.clone()));
            }
            Key::Char('x') => {
                if let Some(a) = self.selected_agent().filter(|a| a.state == "running") {
                    return Effect::Interrupt(a.pane.clone());
                }
            }
            Key::Char('i') => {
                if self.selected_waits() {
                    self.input.clear();
                    self.mode = Mode::Reply;
                }
            }
            Key::Char(c @ '1'..='9') => return self.digit(c as usize - '0' as usize),
            _ => {}
        }
        Effect::None
    }

    fn key_sessions(&mut self, k: Key) -> Effect {
        match k {
            Key::Up | Key::Char('k') => self.session_sel = self.session_sel.saturating_sub(1),
            Key::Down | Key::Char('j') => {
                self.session_sel = (self.session_sel + 1).min(self.sessions.len().saturating_sub(1))
            }
            Key::Enter => {
                return self
                    .target()
                    .map_or(Effect::None, |s| Effect::Switch(s.name.clone()));
            }
            Key::Char('r') => return self.run_action(ActionKind::Rename),
            _ => {}
        }
        Effect::None
    }

    fn key_actions(&mut self, k: Key) -> Effect {
        match k {
            Key::Up | Key::Char('k') => self.action_sel = self.action_sel.saturating_sub(1),
            Key::Down | Key::Char('j') => {
                self.action_sel = (self.action_sel + 1).min(ACTIONS.len() - 1)
            }
            Key::Enter => return self.run_action(ACTIONS[self.action_sel].kind),
            Key::Char('r') => return self.run_action(ActionKind::Rename),
            Key::Char('s') => return self.run_action(ActionKind::Save),
            Key::Char('d') => return self.run_action(ActionKind::Exit),
            _ => {}
        }
        Effect::None
    }

    fn selected_waits(&self) -> bool {
        self.selected_agent()
            .is_some_and(|a| self.shown_state(a) == "check")
    }

    /// 1–3 répond à l'agent sélectionné quand il attend ; sinon 1–9 saute à l'agent de ce numéro.
    fn digit(&mut self, n: usize) -> Effect {
        if self.selected_waits() {
            let a = self.selected_agent().unwrap();
            if n <= a.options.len() {
                let (pane, label) = (a.pane.clone(), a.options[n - 1].clone());
                return self.answer(pane, Some(n), label);
            }
        }
        match self.agents.iter().find(|a| a.jump == Some(n as u8)) {
            Some(a) => Effect::GoTo(a.pane.clone()),
            None => Effect::None,
        }
    }

    fn answer(&mut self, pane: String, choice: Option<usize>, label: String) -> Effect {
        let agent = self.agents.iter().find(|a| a.pane == pane);
        let seen = agent.and_then(|a| a.updated_at);
        // Refus d'une permission (No) : l'agent attend un prompt, aucun hook ne suit
        let refused = agent.is_some_and(|a| a.is_permission()) && choice == Some(3);
        let shown = if refused { "done" } else { "running" };
        self.answered.insert(
            pane.clone(),
            Answered {
                text: label.clone(),
                seen,
                shown,
            },
        );
        let text = if choice.is_none() { Some(label) } else { None };
        Effect::Answer { pane, choice, text }
    }

    /// Réponse par clic sur un bouton [n label].
    pub fn click_answer(&mut self, pane: &str, n: usize) -> Effect {
        match self.agents.iter().find(|a| a.pane == pane) {
            Some(a) if n >= 1 && n <= a.options.len() => {
                let label = a.options[n - 1].clone();
                self.answer(pane.to_string(), Some(n), label)
            }
            _ => Effect::None,
        }
    }

    pub fn start_reply(&mut self) {
        if self.selected_waits() {
            self.input.clear();
            self.mode = Mode::Reply;
        }
    }

    fn key_filter(&mut self, k: Key) -> Effect {
        match k {
            Key::Char(c) => self.filter.push(c),
            Key::Backspace => {
                self.filter.pop();
            }
            Key::Esc => {
                self.filter.clear();
                self.mode = Mode::Normal;
            }
            Key::Enter | Key::Down | Key::Up | Key::Tab => self.mode = Mode::Normal,
            Key::BackTab | Key::Quit => {}
        }
        self.clamp();
        Effect::None
    }

    fn key_reply(&mut self, k: Key) -> Effect {
        match k {
            Key::Char(c) => self.input.push(c),
            Key::Backspace => {
                self.input.pop();
            }
            Key::Esc => self.mode = Mode::Normal,
            Key::Enter => {
                self.mode = Mode::Normal;
                let text = std::mem::take(&mut self.input);
                if let (false, Some(a)) = (text.trim().is_empty(), self.selected_agent()) {
                    let pane = a.pane.clone();
                    return self.answer(pane, None, text);
                }
            }
            _ => {}
        }
        Effect::None
    }

    pub fn count_tab(&self, t: Tab) -> Option<usize> {
        match t {
            Tab::Agents => Some(self.agents.len()),
            Tab::Sessions => Some(self.sessions.len()),
            Tab::Actions => None,
        }
    }
}

pub fn rank(state: &str) -> u8 {
    match state {
        "check" => 0,
        "error" => 1,
        "done" => 2,
        "running" => 3,
        "unknown" => 4,
        "stale" => 5,
        _ => 9,
    }
}

fn pane_num(p: &str) -> u64 {
    p.trim_start_matches('%').parse().unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ag(pane: &str, session: &str, state: &str, jump: u8, options: &[&str]) -> Agent {
        Agent {
            pane: pane.into(),
            session: session.into(),
            state: state.into(),
            jump: Some(jump),
            task: Some(format!("task of {session}")),
            options: options.iter().map(|s| s.to_string()).collect(),
            updated_at: Some(jump as i64),
            ..Default::default()
        }
    }

    fn app() -> App {
        let mut a = App::new("v0".into());
        a.set_agents(vec![
            ag("%1", "prosper", "check", 1, &["pdfplumber", "PyMuPDF"]),
            ag("%2", "notion", "done", 2, &[]),
            ag("%3", "alpha", "running", 3, &[]),
        ]);
        a
    }

    #[test]
    fn digits_answer_a_waiting_agent_and_jump_otherwise() {
        let mut a = app();
        assert_eq!(
            a.key(Key::Char('2')),
            Effect::Answer {
                pane: "%1".into(),
                choice: Some(2),
                text: None
            }
        );
        assert_eq!(a.answered["%1"].text, "PyMuPDF");
        // répondu : affiché running, donc les chiffres sautent de nouveau
        assert_eq!(a.shown_state(&a.agents[0]), "running");
        assert_eq!(a.key(Key::Char('2')), Effect::GoTo("%2".into()));
        assert_eq!(a.key(Key::Char('9')), Effect::None);
    }

    #[test]
    fn digit_beyond_the_options_jumps() {
        let mut a = app();
        assert_eq!(a.key(Key::Char('3')), Effect::GoTo("%3".into()));
    }

    #[test]
    fn free_reply() {
        let mut a = app();
        a.key(Key::Char('i'));
        assert_eq!(a.mode, Mode::Reply);
        for c in "use pypdf".chars() {
            a.key(Key::Char(c));
        }
        assert_eq!(
            a.key(Key::Enter),
            Effect::Answer {
                pane: "%1".into(),
                choice: None,
                text: Some("use pypdf".into())
            }
        );
        assert_eq!(a.mode, Mode::Normal);
    }

    #[test]
    fn filter_narrows_and_esc_clears() {
        let mut a = app();
        a.key(Key::Char('/'));
        for c in "notion".chars() {
            a.key(Key::Char(c));
        }
        assert_eq!(a.visible().len(), 1);
        assert_eq!(a.key(Key::Enter), Effect::None);
        assert_eq!(a.key(Key::Enter), Effect::GoTo("%2".into()));
        a.key(Key::Char('/'));
        a.key(Key::Esc);
        assert_eq!(a.visible().len(), 3);
    }

    #[test]
    fn sorts() {
        let mut a = app();
        let panes = |a: &App| {
            a.visible()
                .iter()
                .map(|x| x.pane.clone())
                .collect::<Vec<_>>()
        };
        assert_eq!(panes(&a), ["%1", "%2", "%3"]);
        a.key(Key::Char('o'));
        assert_eq!(a.sort, Sort::Session);
        assert_eq!(panes(&a), ["%3", "%2", "%1"]);
        a.key(Key::Char('o'));
        assert_eq!(panes(&a), ["%3", "%2", "%1"]);
    }

    #[test]
    fn selection_follows_the_pane_after_refresh() {
        let mut a = app();
        a.key(Key::Down);
        assert_eq!(a.selected_agent().unwrap().pane, "%2");
        let mut agents = a.agents.clone();
        agents.reverse();
        a.set_agents(agents);
        assert_eq!(a.selected_agent().unwrap().pane, "%2");
    }

    #[test]
    fn answer_holds_until_the_state_file_changes() {
        let mut a = app();
        a.key(Key::Char('1'));
        // pas de nouvel événement : toujours affiché running, même après plusieurs rafraîchissements
        a.set_agents(a.agents.clone());
        assert_eq!(a.shown_state(&a.agents[0]), "running");
        // PostToolUse : running avec la note
        let mut agents = a.agents.clone();
        agents[0].state = "running".into();
        agents[0].updated_at = Some(100);
        a.set_agents(agents.clone());
        assert!(a.answered.contains_key("%1"));
        agents[0].state = "done".into();
        agents[0].updated_at = Some(101);
        a.set_agents(agents);
        assert!(!a.answered.contains_key("%1"));
    }

    #[test]
    fn refusing_a_permission_shows_done_until_the_next_event() {
        let mut a = App::new("v0".into());
        a.set_agents(vec![ag("%1", "p", "check", 1, &["Yes", "Always", "No"])]);
        assert_eq!(
            a.key(Key::Char('3')),
            Effect::Answer {
                pane: "%1".into(),
                choice: Some(3),
                text: None
            }
        );
        a.set_agents(a.agents.clone());
        assert_eq!(a.shown_state(&a.agents[0]), "done");
    }

    #[test]
    fn tabs_cycle_and_each_tab_has_its_keys() {
        let mut a = app();
        a.key(Key::Tab);
        assert_eq!(a.tab, Tab::Actions);
        assert_eq!(a.key(Key::Enter), Effect::OpenNew); // ACTIONS : 1re action
        a.key(Key::BackTab);
        a.key(Key::BackTab);
        assert_eq!(a.tab, Tab::Sessions);
        a.set_sessions(
            vec![sess("alpha", "/w/alpha"), sess("prosper", "/w/prosper")],
            "prosper".into(),
        );
        assert_eq!(a.count_tab(Tab::Sessions), Some(2));
    }

    fn sess(n: &str, p: &str) -> Session {
        Session {
            name: n.into(),
            path: p.into(),
        }
    }

    fn with_sessions() -> App {
        let mut a = app();
        a.home = "/h".into();
        a.set_sessions(
            vec![
                sess("api", "/w/a/api"),
                sess("main", "/h"),
                sess("prosper", "/w/prosper"),
            ],
            "main".into(),
        );
        a
    }

    #[test]
    fn cursor_starts_on_the_current_session_and_enter_switches() {
        let mut a = with_sessions();
        a.set_tab(Tab::Sessions);
        assert_eq!(a.target().unwrap().name, "main");
        a.key(Key::Down);
        assert_eq!(a.key(Key::Enter), Effect::Switch("prosper".into()));
        // rafraîchissement : le curseur reste sur prosper
        a.set_sessions(a.sessions.clone(), "main".into());
        assert_eq!(a.target().unwrap().name, "prosper");
    }

    #[test]
    fn new_session_screen_creates_attaches_or_suffixes() {
        let mut a = with_sessions();
        assert_eq!(a.key(Key::Char('N')), Effect::OpenNew);
        a.open_new(vec!["/w/a/api".into(), "/w/b/api".into(), "/w/web".into()]);
        for c in "web".chars() {
            a.key(Key::Char(c));
        }
        assert_eq!(a.new_folders(), vec!["/w/web"]);
        assert_eq!(
            a.key(Key::Enter),
            Effect::Create {
                name: "web".into(),
                dir: "/w/web".into()
            }
        );
        assert!(a.screen.is_none());
        a.open_new(vec!["/w/a/api".into(), "/w/b/api".into()]);
        assert_eq!(a.key(Key::Enter), Effect::Switch("api".into()));
        a.open_new(vec!["/w/a/api".into(), "/w/b/api".into()]);
        a.key(Key::Down);
        assert_eq!(
            a.key(Key::Enter),
            Effect::Create {
                name: "api-2".into(),
                dir: "/w/b/api".into()
            }
        );
        a.open_new(vec!["/w/x".into()]);
        assert_eq!(a.key(Key::Esc), Effect::None);
        assert!(a.screen.is_none());
    }

    #[test]
    fn kill_and_save_exit_screens() {
        let mut a = with_sessions();
        a.key(Key::Char('K'));
        assert_eq!(a.screen, Some(Screen::Kill("main".into())));
        assert_eq!(a.key(Key::Enter), Effect::KillSession("main".into()));
        a.key(Key::Char('Q'));
        assert_eq!(a.screen, Some(Screen::SaveExit));
        assert_eq!(a.key(Key::Char('d')), Effect::Detach);
        a.key(Key::Char('Q'));
        assert_eq!(a.click_button(Button::Confirm), Effect::SaveExit);
        a.key(Key::Char('K'));
        assert_eq!(a.click_button(Button::Cancel), Effect::None);
        assert!(a.screen.is_none());
    }

    #[test]
    fn rename_and_actions() {
        let mut a = with_sessions();
        a.set_tab(Tab::Actions);
        a.key(Key::Char('r'));
        for _ in 0.."main".len() {
            a.key(Key::Backspace);
        }
        for c in "home".chars() {
            a.key(Key::Char(c));
        }
        assert_eq!(
            a.key(Key::Enter),
            Effect::Rename {
                from: "main".into(),
                to: "home".into()
            }
        );
        assert_eq!(a.key(Key::Char('s')), Effect::Save);
        a.key(Key::Down);
        a.key(Key::Down);
        assert_eq!(a.key(Key::Enter), Effect::LastSession);
        assert_eq!(a.click_action(11), Effect::ToggleSidebar);
        assert_eq!(a.click_action(0), Effect::OpenNew);
    }

    #[test]
    fn ctrl_c_quits_but_q_does_not() {
        let mut a = app();
        assert_eq!(a.key(Key::Char('?')), Effect::Help);
        assert_eq!(a.key(Key::Char('q')), Effect::None);
        assert_eq!(a.key(Key::Quit), Effect::Quit);
    }
}
