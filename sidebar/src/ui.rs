//! Rendu de la sidebar. Inspiré de claude-squad : cartes sur deux lignes et plus, fond de
//! sélection, onglets soulignés en accent, menu de touches « touche desc • … » en pied.

use ratatui::Frame;
use ratatui::layout::Rect;
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Paragraph};

use crate::app::{ACTIONS, App, Button, Mode, Screen, Sort, Tab, rank};
use crate::model::{Agent, ago};
use crate::sessions::{Fit, tilde};
use crate::theme::*;

/// Zone cliquable de l'écran.
#[derive(Debug, Clone, PartialEq)]
pub enum Hit {
    Tab(Tab),
    Help,
    Agent(usize),
    Answer(String, usize),
    Reply(String),
    Session(usize),
    Action(usize),
    Button(crate::app::Button),
}

pub const INDENT: &str = "      ";

/// Une ligne en construction : segments, zones cliquables (colonnes) de type `H`, fond.
pub struct Row<H = Hit> {
    spans: Vec<Span<'static>>,
    hits: Vec<(u16, u16, H)>,
    bg: Option<Color>,
    width: u16,
}

impl<H> Default for Row<H> {
    fn default() -> Self {
        Row {
            spans: vec![],
            hits: vec![],
            bg: None,
            width: 0,
        }
    }
}

impl<H: Clone> Row<H> {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn width(&self) -> u16 {
        self.width
    }
    pub fn push(&mut self, text: impl Into<String>, style: Style) -> &mut Self {
        let s = Span::styled(text.into(), style);
        self.width += s.width() as u16;
        self.spans.push(s);
        self
    }
    pub fn hit(&mut self, text: impl Into<String>, style: Style, hit: H) -> &mut Self {
        let x = self.width;
        self.push(text, style);
        self.hits.push((x, self.width, hit));
        self
    }
    pub fn bg(mut self, c: Option<Color>) -> Self {
        self.bg = c;
        self
    }
    fn pad_to_right(&mut self, len: u16, width: u16) {
        let pad = width.saturating_sub(self.width + len);
        self.push(" ".repeat(pad as usize), Style::new());
    }
    /// Texte aligné à droite sur `width` colonnes.
    pub fn right(&mut self, text: impl Into<String>, style: Style, width: u16) -> &mut Self {
        let s: String = text.into();
        self.pad_to_right(Span::raw(s.as_str()).width() as u16, width);
        self.push(s, style)
    }
    /// Zone cliquable alignée à droite.
    pub fn right_hit(
        &mut self,
        text: impl Into<String>,
        style: Style,
        width: u16,
        hit: H,
    ) -> &mut Self {
        let s: String = text.into();
        self.pad_to_right(Span::raw(s.as_str()).width() as u16, width);
        self.hit(s, style, hit)
    }
    /// Fin d'une chaîne push(…) sur une ligne temporaire.
    pub fn done(&mut self) -> Self {
        std::mem::take(self)
    }
    pub fn line(&self, width: u16) -> Line<'static> {
        let mut spans = self.spans.clone();
        if let Some(bg) = self.bg {
            spans.push(Span::raw(
                " ".repeat(width.saturating_sub(self.width) as usize),
            ));
            spans = spans
                .into_iter()
                .map(|s| {
                    let st = s.style.bg(bg);
                    s.style(st)
                })
                .collect();
        }
        Line::from(spans)
    }
}

/// Dessine une ligne en (x, y) sur `w` colonnes et ajoute ses zones cliquables.
pub fn place<H: Clone>(
    f: &mut Frame,
    hits: &mut Vec<(Rect, H)>,
    row: &Row<H>,
    x: u16,
    y: u16,
    w: u16,
) {
    let r = Rect {
        x,
        y,
        width: w,
        height: 1,
    };
    if !f.area().intersects(r) {
        return;
    }
    f.render_widget(Paragraph::new(row.line(w)), r);
    for (a, b, h) in &row.hits {
        hits.push((
            Rect {
                x: x + a,
                y,
                width: b - a,
                height: 1,
            },
            h.clone(),
        ));
    }
}

/// Coupe un texte à `w` colonnes (… en fin).
pub fn cut(s: &str, w: usize) -> String {
    if s.chars().count() <= w {
        return s.to_string();
    }
    let mut out: String = s.chars().take(w.saturating_sub(1)).collect();
    out.push('…');
    out
}

/// Dessine la sidebar et rend les zones cliquables (coordonnées écran).
pub fn draw(f: &mut Frame, app: &mut App) -> Vec<(Rect, Hit)> {
    let area = f.area();
    app.short_tabs = short_tabs(app, area.width);
    let app = &*app;
    f.render_widget(Block::new().style(Style::new().bg(BG).fg(TEXT)), area);
    let w = area.width;
    let mut hits = vec![];
    let mut header = vec![title_row(app, w), tabs_row(app, w)];
    let mut under: Row = Row::new();
    for (i, t) in Tab::ALL.iter().enumerate() {
        let len = tab_label(app, *t).chars().count() as u16 + 2;
        let style = if *t == app.tab { fg(ACCENT) } else { fg(LINE) };
        under.push(
            if *t == app.tab { "━" } else { "─" }.repeat(len as usize),
            style,
        );
        if i < 2 {
            under.push("─", fg(LINE));
        }
    }
    under.push("─".repeat(w.saturating_sub(under.width) as usize), fg(LINE));
    header.push(under);
    for (y, row) in header.iter().enumerate() {
        place(f, &mut hits, row, area.x, area.y + y as u16, w);
    }

    let footer = footer_row(app, w);
    let body = Rect {
        x: area.x,
        y: area.y + 3,
        width: w,
        height: area.height.saturating_sub(5),
    };
    place(
        f,
        &mut hits,
        &Row::new().push("─".repeat(w as usize), fg(LINE)).done(),
        area.x,
        area.bottom().saturating_sub(2),
        w,
    );
    place(
        f,
        &mut hits,
        &footer,
        area.x,
        area.bottom().saturating_sub(1),
        w,
    );

    let (rows, sel) = match (&app.screen, app.tab) {
        (Some(screen), _) => screen_rows(app, screen, w),
        (None, Tab::Agents) => agents_rows(app, w),
        (None, Tab::Sessions) => sessions_rows(app, w),
        (None, Tab::Actions) => actions_rows(app, w),
    };
    let offset = scroll(sel, body.height as usize);
    for (i, row) in rows
        .iter()
        .skip(offset)
        .take(body.height as usize)
        .enumerate()
    {
        place(f, &mut hits, row, body.x, body.y + i as u16, w);
    }
    hits
}

/// Décalage de défilement qui garde la carte sélectionnée (début, fin) visible.
fn scroll(sel: Option<(usize, usize)>, height: usize) -> usize {
    match sel {
        Some((start, end)) if end >= height => (end + 1 - height).min(start),
        _ => 0,
    }
}

fn title_row(app: &App, w: u16) -> Row {
    let mut r = Row::new();
    r.push(
        " AI.files ",
        Style::new().bg(ACCENT).fg(BG).add_modifier(Modifier::BOLD),
    );
    r.right(format!("{} ", app.version), fg(MUTED), w);
    r
}

/// Libellés longs, ou courts quand la barre ne tient pas dans la largeur (case « ? » comprise).
fn short_tabs(app: &App, w: u16) -> bool {
    let long: usize = Tab::ALL
        .iter()
        .map(|t| tab_label_as(app, *t, false).chars().count() + 2)
        .sum::<usize>()
        + 2
        + 3;
    long > w as usize
}

fn tab_label(app: &App, t: Tab) -> String {
    tab_label_as(app, t, app.short_tabs)
}

fn tab_label_as(app: &App, t: Tab, short: bool) -> String {
    let name = match (t, short) {
        (Tab::Sessions, false) => "SESSIONS",
        (Tab::Sessions, true) => "SESS",
        (Tab::Agents, _) => "AGENTS",
        (Tab::Actions, false) => "ACTIONS",
        (Tab::Actions, true) => "ACT",
    };
    match app.count_tab(t) {
        Some(n) => format!("{name} {n}"),
        None => name.to_string(),
    }
}

fn tabs_row(app: &App, w: u16) -> Row {
    let mut r = Row::new();
    for (i, t) in Tab::ALL.iter().enumerate() {
        let style = if *t == app.tab {
            bold(ACCENT)
        } else {
            fg(MUTED)
        };
        r.hit(format!(" {} ", tab_label(app, *t)), style, Hit::Tab(*t));
        if i < 2 {
            r.push("│", fg(LINE));
        }
    }
    // Case « ? » fixe à droite : ouvre l'aide
    let pad = w.saturating_sub(r.width + 3);
    r.push(" ".repeat(pad as usize), Style::new());
    r.hit(" ? ", bold(ACCENT), Hit::Help);
    r
}

fn footer_row(app: &App, w: u16) -> Row {
    let mut r = Row::new();
    if let Some(m) = &app.message {
        r.push(format!(" {}", cut(m, w as usize - 1)), fg(CHECK));
        return r;
    }
    let waits = app
        .selected_agent()
        .is_some_and(|a| app.shown_state(a) == "check");
    let keys: &[(&str, &str)] = match (&app.screen, app.mode, app.tab) {
        (Some(Screen::New { .. }), _, _) => &[
            ("↑↓", "folder"),
            ("type", "filter"),
            ("⏎", "create"),
            ("esc", "cancel"),
        ],
        (Some(Screen::Kill(_)), _, _) => &[("⏎", "save & kill"), ("esc", "cancel")],
        (Some(Screen::SaveExit), _, _) => {
            &[("⏎", "save & exit"), ("d", "exit only"), ("esc", "cancel")]
        }
        (Some(Screen::Rename { .. }), _, _) => &[("⏎", "rename"), ("esc", "cancel")],
        (None, Mode::Filter, _) => &[("type", "filter"), ("⏎", "done"), ("esc", "clear")],
        (None, Mode::Reply, _) => &[("⏎", "send"), ("esc", "cancel")],
        (None, _, Tab::Sessions) => &[
            ("↑↓", "move"),
            ("⏎", "switch"),
            ("r", "rename"),
            ("N", "new"),
            ("K", "kill"),
        ],
        (None, _, Tab::Actions) => &[("↑↓", "move"), ("⏎", "run"), ("s", "save"), ("d", "exit")],
        _ => &[],
    };
    let agent_keys: &[(&str, &str)] = match (app.mode, app.tab) {
        (_, Tab::Agents) if waits => &[
            ("1-3", "answer"),
            ("i", "reply"),
            ("⏎", "go"),
            ("p", "peek"),
        ],
        (_, Tab::Agents) => &[
            ("↑↓", "move"),
            ("⏎", "go"),
            ("p", "peek"),
            ("/", "filter"),
            ("o", "sort"),
        ],
        _ => &[],
    };
    let keys = if keys.is_empty() { agent_keys } else { keys };
    r.push(" ", Style::new());
    let answer = app
        .selected_agent()
        .map_or(String::new(), |a| format!("1-{}", a.options.len().max(1)));
    let help = "? help".len() as u16;
    for (k, d) in keys {
        let k = if *k == "1-3" { answer.as_str() } else { k };
        let len = (k.chars().count() + d.chars().count() + 4) as u16;
        if r.width + len + help > w {
            break;
        }
        r.push(k.to_string(), fg(ACCENT))
            .push(format!(" {d}"), fg(MUTED))
            .push(" • ", fg(TREE));
    }
    r.hit("?", fg(ACCENT), Hit::Help)
        .hit(" help", fg(MUTED), Hit::Help);
    r
}

/// Lignes de l'onglet AGENTS et position (début, fin) de la carte sélectionnée.
pub fn agents_rows(app: &App, w: u16) -> (Vec<Row>, Option<(usize, usize)>) {
    let mut rows = vec![];
    // Filtre et tri
    let mut r = Row::new();
    match (app.mode, app.filter.is_empty()) {
        (Mode::Filter, _) => r
            .push(" / ", fg(ACCENT))
            .push(format!("{}▏", app.filter), fg(TEXT)),
        (_, true) => r.push(" / filter agents, sessions, tasks", fg(MUTED)),
        (_, false) => r.push(" / ", fg(ACCENT)).push(app.filter.clone(), fg(TEXT)),
    };
    r.right(format!("{} ", app.sort.label()), fg(ACCENT), w);
    rows.push(r);
    rows.push(Row::new());

    if let Some(e) = &app.load_error {
        rows.push(
            Row::new()
                .push(format!(" {}", cut(e, w as usize - 1)), fg(ERROR))
                .done(),
        );
    }
    let visible = app.visible();
    if visible.is_empty() {
        let msg = if app.agents.is_empty() {
            " no agents"
        } else {
            " no match"
        };
        rows.push(Row::new().push(msg, fg(MUTED)).done());
        return (rows, None);
    }

    let mut sel = None;
    let mut section = None;
    for (i, a) in visible.iter().enumerate() {
        let state = app.shown_state(a);
        if app.sort == Sort::Priority && section != Some(rank(state)) {
            section = Some(rank(state));
            let n = visible
                .iter()
                .filter(|x| rank(app.shown_state(x)) == rank(state))
                .count();
            let style = if state == "check" {
                bold(CHECK)
            } else {
                bold(MUTED)
            };
            rows.push(
                Row::new()
                    .push(format!(" {}", section_title(state)), style)
                    .push(format!(" {n}"), fg(TREE))
                    .done(),
            );
        }
        let start = rows.len();
        let selected = i == app.selected;
        rows.extend(card(app, a, i, selected, w));
        if selected {
            sel = Some((start, rows.len() - 1));
        }
        rows.push(Row::new());
    }
    (rows, sel)
}

fn stale_after() -> i64 {
    std::env::var("AIF_STALE_AFTER")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(3600)
}

/// Carte d'un agent (lignes à fond de sélection quand elle est choisie).
pub fn card(app: &App, a: &Agent, idx: usize, selected: bool, w: u16) -> Vec<Row> {
    let bg = selected.then_some(SELECTED);
    let state = app.shown_state(a);
    let text_w = (w as usize).saturating_sub(INDENT.len() + 1);
    let mut rows = vec![];

    // 1 : [n] glyphe session outil ……… durée
    let mut r = Row::new().bg(bg);
    let jump = a.jump.map_or("   ".to_string(), |j| format!("[{j}]"));
    r.hit(format!(" {jump} "), fg(MUTED), Hit::Agent(idx));
    r.hit(
        glyph(state, app.tick),
        fg(state_color(state)),
        Hit::Agent(idx),
    );
    r.hit(format!(" {}", a.session), bold(TEXT), Hit::Agent(idx));
    r.hit(format!(" {}", a.tool_name()), fg(MUTED), Hit::Agent(idx));
    let since = if state == "running" {
        a.prompt_at.or(a.updated_at)
    } else {
        a.updated_at
    };
    let dur_style = if state == "stale" {
        fg(CHECK)
    } else {
        fg(MUTED)
    };
    r.right(format!("{} ", ago(app.now, since)), dur_style, w);
    rows.push(r);

    // 2 : tâche
    let task = a
        .task
        .clone()
        .unwrap_or_else(|| a.cwd.clone().unwrap_or_default());
    rows.push(
        Row::new()
            .bg(bg)
            .push(format!("{INDENT}{}", cut(&task, text_w)), fg(TEXT))
            .done(),
    );

    let wrapped = |text: &str, c: Color| -> Vec<Row> {
        textwrap::wrap(text, wrap_opts(text_w.max(8)))
            .iter()
            .map(|l| Row::new().bg(bg).push(format!("{INDENT}{l}"), fg(c)).done())
            .collect()
    };
    if state == "check" {
        let q = a
            .question
            .clone()
            .unwrap_or_else(|| "Waiting for you".into());
        rows.extend(wrapped(&q, CHECK));
        // Boutons [1 label] [2 label] [i Reply…], renvoyés à la ligne si besoin
        let mut r = Row::new().bg(bg);
        r.push(INDENT, Style::new());
        let mut buttons: Vec<(String, Option<usize>)> = a
            .options
            .iter()
            .enumerate()
            .map(|(i, o)| (format!("[{} {}]", i + 1, cut(o, 18)), Some(i + 1)))
            .collect();
        buttons.push(("[i Reply…]".into(), None));
        for (label, n) in buttons {
            let len = label.chars().count() as u16 + 1;
            if r.width + len > w && r.width > INDENT.len() as u16 {
                rows.push(std::mem::take(&mut r).bg(bg));
                r.push(INDENT, Style::new());
            }
            let key_len = label.find(' ').unwrap_or(1);
            let hit = n.map_or(Hit::Reply(a.pane.clone()), |n| {
                Hit::Answer(a.pane.clone(), n)
            });
            r.hit(label[..key_len].to_string(), bold(ACCENT), hit.clone());
            r.hit(label[key_len..].to_string(), fg(TEXT), hit);
            r.push(" ", Style::new());
        }
        rows.push(r.bg(bg));
        if selected && app.mode == Mode::Reply {
            rows.push(
                Row::new()
                    .bg(bg)
                    .push(format!("{INDENT}› "), fg(ACCENT))
                    .push(format!("{}▏", app.input), fg(TEXT))
                    .done(),
            );
        }
    } else {
        // 3 : git, modèle, contexte
        let mut segs: Vec<Vec<(String, Style)>> = vec![];
        if let Some(g) = a.git.as_ref().filter(|g| g.files > 0) {
            segs.push(vec![
                (format!("+{}", g.add), fg(GIT)),
                (format!(" −{}", g.del), fg(ERROR)),
                (
                    format!(" · {} file{}", g.files, if g.files == 1 { "" } else { "s" }),
                    fg(MUTED),
                ),
            ]);
        }
        if let Some(m) = &a.model {
            segs.push(vec![(m.clone(), fg(MUTED))]);
        }
        if let Some(c) = a.ctx {
            let style = if c >= 80.0 { fg(CHECK) } else { fg(MUTED) };
            segs.push(vec![(format!("{} {}%", ctx_bar(c), c.round()), style)]);
        }
        let mut r = Row::new().bg(bg);
        r.push(INDENT, Style::new());
        for seg in segs {
            let len: u16 = seg
                .iter()
                .map(|(t, _)| t.chars().count() as u16)
                .sum::<u16>()
                + 2;
            if r.width > INDENT.len() as u16 && r.width + len > w {
                rows.push(std::mem::take(&mut r).bg(bg));
                r.push(INDENT, Style::new());
            } else if r.width > INDENT.len() as u16 {
                r.push("  ", Style::new());
            }
            for (t, st) in seg {
                r.push(t, st);
            }
        }
        if r.width > INDENT.len() as u16 {
            rows.push(r);
        }
        let note = |text: String, c: Color| wrapped(&text, c);
        if a.ctx.is_some_and(|c| c >= 80.0) {
            rows.extend(note("context almost full".into(), CHECK));
        }
        match state {
            "stale" => rows.extend(note(
                format!(
                    "no activity for {} (stale after {} min)",
                    ago(app.now, a.updated_at),
                    stale_after() / 60
                ),
                CHECK,
            )),
            "error" => rows.extend(note(
                a.error.clone().unwrap_or_else(|| "error".into()),
                ERROR,
            )),
            "unknown" => rows.extend(note("agent detected, no hook received".into(), MUTED)),
            _ => {}
        }
        if let Some(ans) = app.answered.get(&a.pane) {
            rows.extend(note(format!("you answered: {}", ans.text), MUTED));
        }
    }

    // Sous-agents : arbre ├ / └
    let subs: Vec<_> = a.subagents.values().collect();
    for (i, s) in subs.iter().enumerate() {
        let branch = if i + 1 == subs.len() { "└" } else { "├" };
        let st = if s.state == "running" {
            "running"
        } else {
            "done"
        };
        let mut r = Row::new().bg(bg);
        r.push(format!("{INDENT}{branch} "), fg(TREE))
            .push(glyph(st, app.tick), fg(state_color(st)))
            .push(format!(" {}", s.kind), fg(TEXT));
        if st == "done" {
            r.push("  done", fg(MUTED));
        }
        rows.push(r);
    }
    rows
}

/// Retour à la ligne aux espaces seulement : « prosper-2 » ou « --resume » restent entiers.
fn wrap_opts(width: usize) -> textwrap::Options<'static> {
    textwrap::Options::new(width).word_splitter(textwrap::WordSplitter::NoHyphenation)
}

/// Compte des agents par état, dans l'ordre de priorité : « ◉1 ⠹2 ».
fn state_counts(app: &App, agents: &[&Agent], r: &mut Row) {
    let mut states: Vec<&str> = agents.iter().map(|a| app.shown_state(a)).collect();
    states.sort_by_key(|s| rank(s));
    states.dedup();
    for st in states {
        let n = agents.iter().filter(|a| app.shown_state(a) == st).count();
        r.push(format!("{}{n} ", glyph(st, app.tick)), fg(state_color(st)));
    }
}

/// Onglet SESSIONS : arbre session → agents → sous-agents.
pub fn sessions_rows(app: &App, w: u16) -> (Vec<Row>, Option<(usize, usize)>) {
    let mut rows = vec![];
    let mut sel = None;
    if app.sessions.is_empty() {
        rows.push(Row::new().push(" no sessions", fg(MUTED)).done());
    }
    for (i, s) in app.sessions.iter().enumerate() {
        let start = rows.len();
        let current = s.name == app.current;
        let bg = (i == app.session_sel).then_some(SELECTED);
        let agents = app.agents_of(&s.name);
        let mut r = Row::new().bg(bg);
        r.hit(
            if current { "▸" } else { " " },
            bold(ACCENT),
            Hit::Session(i),
        );
        r.hit(format!(" {:02} ", i + 1), fg(MUTED), Hit::Session(i));
        r.hit(
            s.name.clone(),
            if current { bold(ACCENT) } else { fg(TEXT) },
            Hit::Session(i),
        );
        let mut counts = Row::new();
        state_counts(app, &agents, &mut counts);
        let cw = counts.width();
        r.push(
            " ".repeat(w.saturating_sub(r.width() + cw) as usize),
            Style::new(),
        );
        state_counts(app, &agents, &mut r);
        rows.push(r);
        rows.push(
            Row::new()
                .bg(bg)
                .push(
                    format!("     {}", cut(&tilde(&s.path, &app.home), w as usize - 6)),
                    fg(MUTED),
                )
                .done(),
        );
        if agents.is_empty() {
            rows.push(Row::new().bg(bg).push("     no agents", fg(TREE)).done());
        }
        for (j, a) in agents.iter().enumerate() {
            let last = j + 1 == agents.len();
            let state = app.shown_state(a);
            let mut r = Row::new().bg(bg);
            r.push(format!("     {} ", if last { "└" } else { "├" }), fg(TREE));
            r.push(glyph(state, app.tick), fg(state_color(state)));
            r.push(format!(" {} ", a.tool_name()), fg(MUTED));
            let since = if state == "running" {
                a.prompt_at.or(a.updated_at)
            } else {
                a.updated_at
            };
            let dur = ago(app.now, since);
            let room = (w as usize).saturating_sub(r.width() as usize + dur.chars().count() + 2);
            r.push(cut(a.task.as_deref().unwrap_or(""), room), fg(TEXT));
            r.right(format!("{dur} "), fg(MUTED), w);
            rows.push(r);
            let subs: Vec<_> = a.subagents.values().collect();
            for (k, sa) in subs.iter().enumerate() {
                let st = if sa.state == "running" {
                    "running"
                } else {
                    "done"
                };
                let mut r = Row::new().bg(bg);
                r.push(
                    format!(
                        "     {}    {} ",
                        if last { " " } else { "│" },
                        if k + 1 == subs.len() { "└" } else { "├" }
                    ),
                    fg(TREE),
                );
                r.push(glyph(st, app.tick), fg(state_color(st)))
                    .push(format!(" {}", sa.kind), fg(TEXT));
                if st == "done" {
                    r.push("  done", fg(MUTED));
                }
                rows.push(r);
            }
        }
        if i == app.session_sel {
            sel = Some((start, rows.len() - 1));
        }
        rows.push(Row::new());
    }
    (rows, sel)
}

/// Onglet ACTIONS : session visée, puis actions groupées.
pub fn actions_rows(app: &App, w: u16) -> (Vec<Row>, Option<(usize, usize)>) {
    let mut rows = vec![];
    let mut r = Row::new();
    r.push(" TARGET ", bold(MUTED));
    if let Some(t) = app.target() {
        r.push(t.name.clone(), bold(TEXT)).push(
            format!(" {}", cut(&tilde(&t.path, &app.home), w as usize / 2)),
            fg(MUTED),
        );
    }
    rows.push(r);
    let mut sel = None;
    let mut group = "";
    for (i, a) in ACTIONS.iter().enumerate() {
        if a.group != group {
            group = a.group;
            rows.push(Row::new());
            rows.push(Row::new().push(format!(" {group}"), bold(MUTED)).done());
        }
        let start = rows.len();
        let bg = (i == app.action_sel).then_some(SELECTED);
        let mut r = Row::new().bg(bg);
        r.hit(format!("   {} ", a.icon), fg(ACCENT), Hit::Action(i));
        r.hit(a.label, fg(TEXT), Hit::Action(i));
        r.right(format!("{} ", a.keys), fg(ACCENT), w);
        rows.push(r);
        let note = match a.kind {
            crate::app::ActionKind::Save => match app.last_save {
                Some(t) => format!("last save {} ago", ago(app.now, Some(t))),
                None => "no save yet".into(),
            },
            _ => a.note.to_string(),
        };
        if !note.is_empty() {
            rows.push(
                Row::new()
                    .bg(bg)
                    .push(format!("     {}", cut(&note, w as usize - 6)), fg(MUTED))
                    .done(),
            );
        }
        if i == app.action_sel {
            sel = Some((start, rows.len() - 1));
        }
    }
    (rows, sel)
}

fn wrap_rows(text: &str, w: u16, style: Style) -> Vec<Row> {
    textwrap::wrap(text, wrap_opts((w as usize).saturating_sub(2).max(8)))
        .iter()
        .map(|l| Row::new().push(format!(" {l}"), style).done())
        .collect()
}

fn buttons(cancel: &str, confirm: &str, confirm_style: Style) -> Row {
    let mut r = Row::new();
    r.push(" ", Style::new());
    r.hit(
        format!("[ {cancel} ]"),
        fg(MUTED),
        Hit::Button(Button::Cancel),
    );
    r.push("  ", Style::new());
    r.hit(
        format!("[ {confirm} ]"),
        confirm_style,
        Hit::Button(Button::Confirm),
    );
    r
}

/// Écrans de confirmation : New session, Kill session, Save & exit, Rename.
pub fn screen_rows(app: &App, screen: &Screen, w: u16) -> (Vec<Row>, Option<(usize, usize)>) {
    let mut rows = vec![];
    let mut sel = None;
    let agent_row = |a: &Agent, with_session: bool| {
        let st = app.shown_state(a);
        let mut r = Row::new();
        r.push("   ", Style::new())
            .push(glyph(st, app.tick), fg(state_color(st)));
        if with_session {
            r.push(format!(" {}", a.session), bold(TEXT));
        }
        r.push(format!(" {} ", a.tool_name()), fg(MUTED));
        let room = (w as usize).saturating_sub(r.width() as usize + 1);
        r.push(cut(a.task.as_deref().unwrap_or(""), room), fg(TEXT));
        r
    };
    match screen {
        Screen::New { filter, .. } => {
            rows.push(Row::new().push(" NEW SESSION", bold(ACCENT)).done());
            let mut r = Row::new();
            r.push(" / ", fg(ACCENT));
            if filter.is_empty() {
                r.push("filter folders▏", fg(MUTED));
            } else {
                r.push(format!("{filter}▏"), fg(TEXT));
            }
            rows.push(r);
            rows.push(Row::new());
            let folders = app.new_folders();
            if folders.is_empty() {
                rows.push(Row::new().push(" no folder", fg(MUTED)).done());
            }
            for (i, d) in folders.iter().enumerate() {
                let selected = i == app.new_sel();
                let (label, color) = match app.fit_of(d) {
                    Fit::New(_) => ("new".to_string(), DONE),
                    Fit::Attach(n) => (format!("attach {n}"), RUNNING),
                    Fit::Taken { name, .. } => (format!("name taken → {name}"), CHECK),
                };
                let mut r = Row::new().bg(selected.then_some(SELECTED));
                let room = (w as usize).saturating_sub(label.chars().count() + 4);
                r.hit(
                    format!("  {}", cut(&tilde(d, &app.home), room)),
                    fg(TEXT),
                    Hit::Button(Button::Folder(i)),
                );
                r.right(format!("{label} "), fg(color), w);
                if selected {
                    sel = Some((rows.len(), rows.len()));
                }
                rows.push(r);
            }
            rows.push(Row::new());
            if let Some(d) = folders.get(app.new_sel()) {
                let fit = app.fit_of(d);
                if let Fit::Taken { by, name } = &fit {
                    rows.extend(wrap_rows(
                        &format!(
                            "Name taken by {}: the session is named {name}.",
                            tilde(by, &app.home)
                        ),
                        w,
                        fg(CHECK),
                    ));
                }
                rows.push(Row::new());
                let confirm = if matches!(fit, Fit::Attach(_)) {
                    "Attach"
                } else {
                    "Create & attach"
                };
                rows.push(buttons("Cancel", confirm, bold(ACCENT)));
                if sel.is_some_and(|(_, e)| e + 4 < rows.len()) {
                    sel = sel.map(|(s, _)| (s, rows.len() - 1));
                }
            }
        }
        Screen::Kill(name) => {
            rows.push(
                Row::new()
                    .push(format!(" KILL SESSION {name}"), bold(ERROR))
                    .done(),
            );
            rows.push(Row::new());
            let agents = app.agents_of(name);
            if agents.is_empty() {
                rows.push(
                    Row::new()
                        .push(" No agents in this session.", fg(MUTED))
                        .done(),
                );
            } else {
                rows.push(Row::new().push(" These agents will stop:", fg(TEXT)).done());
                rows.extend(agents.iter().map(|a| agent_row(a, false)));
            }
            rows.push(Row::new());
            rows.extend(wrap_rows("The layout is saved first and can be restored. Agent conversations are not resumed.", w, fg(MUTED)));
            rows.push(Row::new());
            rows.push(buttons("Cancel", "Save & kill", bold(ERROR)));
        }
        Screen::SaveExit => {
            rows.push(Row::new().push(" SAVE & EXIT", bold(ACCENT)).done());
            rows.push(Row::new());
            rows.extend(wrap_rows(
                &format!("Save all {} sessions, then quit tmux.", app.sessions.len()),
                w,
                fg(TEXT),
            ));
            if !app.agents.is_empty() {
                rows.push(Row::new());
                rows.push(Row::new().push(" These agents will stop:", fg(TEXT)).done());
                rows.extend(app.agents.iter().map(|a| agent_row(a, true)));
            }
            rows.push(Row::new());
            rows.extend(wrap_rows(
                "Next start restores the layout. Resume agents with claude --resume.",
                w,
                fg(MUTED),
            ));
            rows.push(Row::new());
            rows.push(buttons("Cancel", "Save & exit", bold(ACCENT)));
            rows.push(Row::new());
            let mut r = Row::new();
            r.push(" ", Style::new()).hit(
                "Exit only, keep everything running (d)",
                fg(RUNNING),
                Hit::Button(Button::ExitOnly),
            );
            rows.push(r);
        }
        Screen::Rename { session, input } => {
            rows.push(
                Row::new()
                    .push(format!(" RENAME SESSION {session}"), bold(ACCENT))
                    .done(),
            );
            rows.push(Row::new());
            rows.push(
                Row::new()
                    .push(" › ", fg(ACCENT))
                    .push(format!("{input}▏"), fg(TEXT))
                    .done(),
            );
        }
    }
    (rows, sel)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::{Git, Subagent};
    use crate::sessions::Session;
    use ratatui::Terminal;
    use ratatui::backend::TestBackend;

    fn screen(app: &mut App, w: u16, h: u16) -> (String, Vec<(Rect, Hit)>) {
        let mut t = Terminal::new(TestBackend::new(w, h)).unwrap();
        let mut hits = vec![];
        t.draw(|f| hits = draw(f, app)).unwrap();
        let buf = t.backend().buffer().clone();
        let text = (0..h)
            .map(|y| {
                (0..w)
                    .map(|x| buf[(x, y)].symbol().to_string())
                    .collect::<String>()
            })
            .collect::<Vec<_>>()
            .join("\n");
        (text, hits)
    }

    fn demo() -> App {
        let mut app = App::new("v0.15.2".into());
        app.now = 10_000;
        let mut check = Agent {
            pane: "%1".into(),
            session: "prosper".into(),
            state: "check".into(),
            jump: Some(1),
            task: Some("Parse the BOAMP notice PDFs".into()),
            question: Some("Which parser for BOAMP notices?".into()),
            options: vec!["pdfplumber".into(), "PyMuPDF".into()],
            updated_at: Some(9_880),
            ..Default::default()
        };
        check.tool = Some("claude".into());
        let mut running = Agent {
            pane: "%2".into(),
            session: "notion-pilot".into(),
            state: "running".into(),
            jump: Some(2),
            task: Some("Refactor the OAuth wizard".into()),
            model: Some("Opus".into()),
            ctx: Some(61.0),
            git: Some(Git {
                add: 42,
                del: 18,
                files: 3,
            }),
            prompt_at: Some(10_000 - 14 * 60),
            ..Default::default()
        };
        running.subagents.insert(
            "a".into(),
            Subagent {
                kind: "Explore".into(),
                state: "running".into(),
            },
        );
        running.subagents.insert(
            "b".into(),
            Subagent {
                kind: "Plan".into(),
                state: "done".into(),
            },
        );
        let stale = Agent {
            pane: "%3".into(),
            session: "old".into(),
            state: "stale".into(),
            jump: Some(3),
            task: Some("Old work".into()),
            updated_at: Some(10_000 - 7_800),
            ..Default::default()
        };
        app.set_agents(vec![check, running, stale]);
        app.home = "/h".into();
        app.set_sessions(
            vec![
                Session {
                    name: "notion-pilot".into(),
                    path: "/h/dev/notion-pilot".into(),
                },
                Session {
                    name: "prosper".into(),
                    path: "/h/dev/prosper".into(),
                },
                Session {
                    name: "old".into(),
                    path: "/h/old".into(),
                },
                Session {
                    name: "empty".into(),
                    path: "/h".into(),
                },
            ],
            "notion-pilot".into(),
        );
        app
    }

    #[test]
    fn agents_tab_matches_the_mockup() {
        let (s, _) = screen(&mut demo(), 60, 40);
        println!("{s}");
        for want in [
            " AI.files ",
            "v0.15.2",
            "SESSIONS 4",
            "AGENTS 3",
            "ACTIONS",
            " ? ",
            "/ filter agents, sessions, tasks",
            "priority",
            "TO CHECK 1",
            "[1] ◉ prosper claude",
            "2 min",
            "Which parser for BOAMP notices?",
            "[1 pdfplumber] [2 PyMuPDF] [i Reply…]",
            "RUNNING 1",
            "notion-pilot claude",
            "14 min",
            "Refactor the OAuth wizard",
            "+42 −18 · 3 files  Opus  ▰▰▰▰▰▰▱▱▱▱ 61%",
            "├ ",
            "Explore",
            "└ ✓ Plan  done",
            "STALE 1",
            "2 h 10",
            "no activity for 2 h 10 (stale after 60 min)",
            "1-2 answer • i reply • ⏎ go • p peek • ? help",
        ] {
            assert!(s.contains(want), "missing {want:?}\n{s}");
        }
    }

    #[test]
    fn buttons_and_tabs_are_clickable() {
        let (_, hits) = screen(&mut demo(), 60, 40);
        assert!(hits.iter().any(|(_, h)| *h == Hit::Answer("%1".into(), 2)));
        assert!(hits.iter().any(|(_, h)| *h == Hit::Reply("%1".into())));
        assert!(hits.iter().any(|(_, h)| *h == Hit::Tab(Tab::Sessions)));
        assert!(hits.iter().any(|(_, h)| *h == Hit::Help));
    }

    #[test]
    fn context_almost_full_from_80_percent() {
        let mut app = demo();
        app.agents[1].ctx = Some(85.0);
        let (s, _) = screen(&mut app, 60, 40);
        assert!(s.contains("context almost full"));
    }

    #[test]
    fn narrow_sidebar_wraps_buttons_and_keeps_the_selection_visible() {
        let mut app = demo();
        app.key(crate::app::Key::Down);
        app.key(crate::app::Key::Down);
        let (s, _) = screen(&mut app, 34, 14);
        println!("{s}");
        assert!(s.contains("old claude"), "{s}");
        assert!(
            s.contains("SESS 4 │ AGENTS 3 │ ACT") && s.contains(" ? "),
            "{s}"
        );
        assert!(s.trim_end().ends_with("? help"), "{s}");
        assert!(
            s.contains("no activity for 2 h 10") && s.contains("(stale after 60 min)"),
            "{s}"
        );
    }

    #[test]
    fn sessions_tab_is_a_tree() {
        let mut app = demo();
        app.set_tab(Tab::Sessions);
        let (s, hits) = screen(&mut app, 60, 40);
        println!("{s}");
        for want in [
            "▸ 01 notion-pilot",
            "⠋1",
            "~/dev/notion-pilot",
            "└ ⠋ claude Refactor the OAuth wizard",
            "14 min",
            "     ├ ⠋ Explore",
            " 02 prosper",
            "◉1",
            " 04 empty",
            "no agents",
            "↑↓ move • ⏎ switch • r rename • N new • K kill • ? help",
        ] {
            assert!(s.contains(want), "missing {want:?}\n{s}");
        }
        assert!(hits.iter().any(|(_, h)| *h == Hit::Session(1)));
    }

    #[test]
    fn actions_tab_lists_the_actions_for_the_target() {
        let mut app = demo();
        app.set_tab(Tab::Actions);
        app.last_save = Some(app.now - 180);
        let (s, hits) = screen(&mut app, 60, 45);
        println!("{s}");
        for want in [
            "TARGET notion-pilot ~/dev/notion-pilot",
            "SESSION",
            "+ New session…",
            "⌃⇧N",
            "pick a folder, name comes from it",
            "✕ Kill session…",
            "⌃⇧K",
            "PANES",
            "┃ Split right",
            "SAVE & EXIT",
            "↓ Save now",
            "last save 3 min ago",
            "⇣ Save & exit…",
            "prefix Q",
            "detach: sessions and agents keep running",
            "↺ Restore last save",
            "VIEW",
            "◧ Hide sidebar",
            "⌃⇧B",
        ] {
            assert!(s.contains(want), "missing {want:?}\n{s}");
        }
        assert!(hits.iter().any(|(_, h)| *h == Hit::Action(11)));
    }

    #[test]
    fn new_session_screen_labels_each_folder() {
        let mut app = demo();
        app.open_new(vec![
            "/h/dev/prosper".into(),
            "/h/other/prosper".into(),
            "/h/dev/web".into(),
        ]);
        let (s, hits) = screen(&mut app, 60, 30);
        println!("{s}");
        for want in [
            "NEW SESSION",
            "/ filter folders",
            "~/dev/prosper",
            "attach prosper",
            "~/other/prosper",
            "name taken → prosper-2",
            "~/dev/web",
            "new",
            "[ Cancel ]  [ Attach ]",
        ] {
            assert!(s.contains(want), "missing {want:?}\n{s}");
        }
        assert!(
            hits.iter()
                .any(|(_, h)| *h == Hit::Button(Button::Folder(2)))
        );
        app.key(crate::app::Key::Down);
        let (s, _) = screen(&mut app, 60, 30);
        assert!(
            s.contains("Name taken by ~/dev/prosper: the session is named")
                && s.contains("prosper-2.")
                && s.contains("[ Create & attach ]"),
            "{s}"
        );
    }

    #[test]
    fn kill_and_save_exit_screens_list_the_agents() {
        let mut app = demo();
        app.key(crate::app::Key::Char('K'));
        let (s, _) = screen(&mut app, 60, 30);
        println!("{s}");
        for want in [
            "KILL SESSION notion-pilot",
            "These agents will stop:",
            "Refactor the OAuth wizard",
            "The layout is saved first and can be restored.",
            "[ Cancel ]  [ Save & kill ]",
            "⏎ save & kill • esc cancel",
        ] {
            assert!(s.contains(want), "missing {want:?}\n{s}");
        }
        app.key(crate::app::Key::Esc);
        app.key(crate::app::Key::Char('Q'));
        let (s, hits) = screen(&mut app, 60, 30);
        println!("{s}");
        for want in [
            "SAVE & EXIT",
            "Save all 4 sessions, then quit tmux.",
            "prosper claude Parse",
            "--resume.",
            "[ Save & exit ]",
            "Exit only, keep everything running (d)",
        ] {
            assert!(s.contains(want), "missing {want:?}\n{s}");
        }
        assert!(
            hits.iter()
                .any(|(_, h)| *h == Hit::Button(Button::ExitOnly))
        );
    }
}
