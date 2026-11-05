//! État de la sidebar et touches. Aucun effet de bord ici : chaque touche rend un `Effect`
//! que `main` exécute (tmux), ce qui garde ce module testable.

use std::collections::HashMap;

use crate::model::Agent;

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
}

/// Réponse envoyée : affichée « you answered: … » tant que l'agent n'a pas changé d'état.
#[derive(Debug, Clone)]
pub struct Answered {
    pub text: String,
    pub at: i64,
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
}

/// Délai pendant lequel un agent qui vient d'être répondu s'affiche en running,
/// le temps que son hook PostToolUse arrive.
const ANSWER_GRACE: i64 = 15;

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
        }
    }

    /// Nouvelle liste d'agents (rafraîchissement) : garde la sélection sur le même pane.
    pub fn set_agents(&mut self, agents: Vec<Agent>) {
        let keep = self.selected_agent().map(|a| a.pane.clone());
        self.agents = agents;
        let now = self.now;
        let states: HashMap<String, String> = self
            .agents
            .iter()
            .map(|a| (a.pane.clone(), a.state.clone()))
            .collect();
        self.answered
            .retain(|pane, ans| match states.get(pane).map(String::as_str) {
                Some("running") => true,
                Some("check") => now - ans.at < ANSWER_GRACE,
                _ => false,
            });
        if let Some(pane) = keep
            && let Some(i) = self.visible().iter().position(|a| a.pane == pane)
        {
            self.selected = i;
        }
        self.clamp();
    }

    /// État affiché : un agent répondu il y a peu reste « running » même si le fichier dit encore check.
    pub fn shown_state<'a>(&self, a: &'a Agent) -> &'a str {
        if a.state == "check" && self.answered.contains_key(&a.pane) {
            "running"
        } else {
            &a.state
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
        match self.mode {
            Mode::Filter => return self.key_filter(k),
            Mode::Reply => return self.key_reply(k),
            Mode::Normal => {}
        }
        match k {
            Key::Tab => self.set_tab(self.tab.next()),
            Key::BackTab => self.set_tab(self.tab.prev()),
            Key::Char('q') => return Effect::Quit,
            Key::Char('?') => self.message = Some("Help view comes with step 5".into()),
            _ if self.tab != Tab::Agents => {}
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
        self.answered.insert(
            pane.clone(),
            Answered {
                text: label.clone(),
                at: self.now,
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
            Key::BackTab => {}
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
            Tab::Sessions => {
                let mut s: Vec<&str> = self.agents.iter().map(|a| a.session.as_str()).collect();
                s.sort();
                s.dedup();
                Some(s.len())
            }
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
    fn answered_note_lasts_while_running_then_clears() {
        let mut a = app();
        a.now = 100;
        a.key(Key::Char('1'));
        let mut agents = a.agents.clone();
        agents[0].state = "running".into();
        a.set_agents(agents.clone());
        assert!(a.answered.contains_key("%1"));
        agents[0].state = "done".into();
        a.set_agents(agents);
        assert!(!a.answered.contains_key("%1"));
    }

    #[test]
    fn tabs_cycle_and_other_tabs_ignore_agent_keys() {
        let mut a = app();
        a.key(Key::Tab);
        assert_eq!(a.tab, Tab::Actions);
        assert_eq!(a.key(Key::Enter), Effect::None);
        a.key(Key::BackTab);
        a.key(Key::BackTab);
        assert_eq!(a.tab, Tab::Sessions);
        assert_eq!(a.count_tab(Tab::Sessions), Some(3));
    }
}
