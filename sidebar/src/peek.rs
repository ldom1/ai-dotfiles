//! Aperçu d'un agent (popup tmux à droite) : onglets Output (capture du pane) et Diff.

use ratatui::Frame;
use ratatui::layout::Rect;
use ratatui::style::Style;
use ratatui::widgets::{Block, Paragraph};

use crate::app::Key;
use crate::model::{Agent, Diff};
use crate::theme::*;
use crate::ui::{Row, cut, place};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PeekTab {
    Output,
    Diff,
}

#[derive(Debug, Clone, PartialEq)]
pub enum PeekHit {
    Tab(PeekTab),
    Close,
    Go,
}

#[derive(Debug, Clone, PartialEq)]
pub enum PeekEffect {
    None,
    Close,
    GoTo(String),
}

pub struct Peek {
    pub pane: String,
    pub tab: PeekTab,
    pub agent: Option<Agent>,
    pub output: String,
    pub diff: Option<Diff>,
    pub error: Option<String>,
    pub tick: usize,
}

impl Peek {
    pub fn new(pane: String) -> Peek {
        Peek {
            pane,
            tab: PeekTab::Output,
            agent: None,
            output: String::new(),
            diff: None,
            error: None,
            tick: 0,
        }
    }

    pub fn key(&mut self, k: Key) -> PeekEffect {
        match k {
            Key::Tab | Key::BackTab => {
                self.tab = if self.tab == PeekTab::Output {
                    PeekTab::Diff
                } else {
                    PeekTab::Output
                };
                PeekEffect::None
            }
            Key::Esc | Key::Char('q') => PeekEffect::Close,
            Key::Enter => PeekEffect::GoTo(self.pane.clone()),
            _ => PeekEffect::None,
        }
    }

    pub fn click(&mut self, h: &PeekHit) -> PeekEffect {
        match h {
            PeekHit::Tab(t) => {
                self.tab = *t;
                PeekEffect::None
            }
            PeekHit::Close => PeekEffect::Close,
            PeekHit::Go => PeekEffect::GoTo(self.pane.clone()),
        }
    }
}

pub fn draw(f: &mut Frame, p: &Peek) -> Vec<(Rect, PeekHit)> {
    let area = f.area();
    f.render_widget(Block::new().style(Style::new().bg(BG).fg(TEXT)), area);
    // Bordure gauche accent
    for y in area.top()..area.bottom() {
        f.render_widget(
            Paragraph::new("▎").style(fg(ACCENT)),
            Rect {
                x: area.x,
                y,
                width: 1,
                height: 1,
            },
        );
    }
    let inner = Rect {
        x: area.x + 1,
        width: area.width.saturating_sub(1),
        ..area
    };
    let w = inner.width;
    let mut hits: Vec<(Rect, PeekHit)> = vec![];
    let put = |f: &mut Frame, row: &Row<PeekHit>, y: u16, hits: &mut Vec<(Rect, PeekHit)>| {
        if y < inner.bottom() {
            place(f, hits, row, inner.x, y, w);
        }
    };
    let state = p.agent.as_ref().map_or("unknown", |a| a.state.as_str());
    let (session, task) = p
        .agent
        .as_ref()
        .map_or((p.pane.clone(), String::new()), |a| {
            (a.session.clone(), a.task.clone().unwrap_or_default())
        });

    // En-tête : PEEK ◉ session tâche ✕
    let mut r = Row::new();
    r.push(" PEEK ", bold(ACCENT))
        .push(glyph(state, p.tick), fg(state_color(state)))
        .push(format!(" {session} "), bold(TEXT));
    let room = (w as usize).saturating_sub(r.width() as usize + 3);
    r.push(cut(&task, room), fg(MUTED));
    r.right_hit(" ✕ ", fg(MUTED), w, PeekHit::Close);
    put(f, &r, inner.y, &mut hits);

    // Onglets Output | Diff +a −d, modèle et contexte à droite
    let (add, del) = p.diff.as_ref().map_or((0, 0), |d| {
        d.files
            .iter()
            .fold((0, 0), |(a, b), x| (a + x.add, b + x.del))
    });
    let mut r = Row::new();
    let tab_style = |t: PeekTab| if p.tab == t { bold(ACCENT) } else { fg(MUTED) };
    r.hit(
        " Output ",
        tab_style(PeekTab::Output),
        PeekHit::Tab(PeekTab::Output),
    );
    r.push("│", fg(LINE));
    r.hit(
        " Diff ",
        tab_style(PeekTab::Diff),
        PeekHit::Tab(PeekTab::Diff),
    );
    r.push(format!("+{add}"), fg(GIT))
        .push(format!(" −{del} "), fg(ERROR));
    if let Some(a) = &p.agent {
        let model = a.model.clone().unwrap_or_default();
        let ctx = a
            .ctx
            .map_or(String::new(), |c| format!(" · ctx {}%", c.round()));
        r.right(format!("{model}{ctx} "), fg(MUTED), w);
    }
    put(f, &r, inner.y + 1, &mut hits);
    put(
        f,
        &Row::new().push("─".repeat(w as usize), fg(LINE)).done(),
        inner.y + 2,
        &mut hits,
    );

    // Corps
    let body_h = inner.height.saturating_sub(6) as usize;
    let rows: Vec<Row<PeekHit>> = match (&p.error, p.tab) {
        (Some(e), _) => vec![Row::new().push(format!(" {e}"), fg(ERROR)).done()],
        (None, PeekTab::Output) => {
            let lines: Vec<&str> = p.output.trim_end().lines().collect();
            lines[lines.len().saturating_sub(body_h)..]
                .iter()
                .map(|l| {
                    Row::new()
                        .push(format!(" {}", cut(l, w as usize - 1)), fg(TEXT))
                        .done()
                })
                .collect()
        }
        (None, PeekTab::Diff) => diff_rows(p.diff.as_ref(), w),
    };
    for (i, r) in rows.iter().take(body_h).enumerate() {
        put(f, r, inner.y + 3 + i as u16, &mut hits);
    }

    // Pied
    let bottom = inner.bottom();
    put(
        f,
        &Row::new().push("─".repeat(w as usize), fg(LINE)).done(),
        bottom.saturating_sub(3),
        &mut hits,
    );
    put(
        f,
        &Row::new()
            .push(
                cut(
                    " dashboard stays open · ⇥ output/diff · esc close",
                    w as usize,
                ),
                fg(MUTED),
            )
            .done(),
        bottom.saturating_sub(2),
        &mut hits,
    );
    let mut r = Row::new();
    r.right_hit(
        " ⏎ Go to agent ",
        Style::new()
            .bg(ACCENT)
            .fg(BG)
            .add_modifier(ratatui::style::Modifier::BOLD),
        w,
        PeekHit::Go,
    );
    put(f, &r, bottom.saturating_sub(1), &mut hits);
    hits
}

/// Liste « fichier +a −d », puis le premier hunk coloré.
fn diff_rows(diff: Option<&Diff>, w: u16) -> Vec<Row<PeekHit>> {
    let Some(d) = diff else {
        return vec![Row::new().push(" loading…", fg(MUTED)).done()];
    };
    if d.files.is_empty() {
        return vec![
            Row::new()
                .push(" no changes against HEAD", fg(MUTED))
                .done(),
        ];
    }
    let mut rows = vec![];
    for x in &d.files {
        let mut r = Row::new();
        r.push(
            format!(" {}", cut(&x.file, (w as usize).saturating_sub(14))),
            fg(TEXT),
        );
        r.right(format!("+{} ", x.add), fg(GIT), w.saturating_sub(5))
            .push(format!("−{}", x.del), fg(ERROR));
        rows.push(r);
    }
    rows.push(Row::new());
    for l in d.hunk.lines() {
        let c = match l.chars().next() {
            Some('+') => GIT,
            Some('-') => ERROR,
            Some('@') => ACCENT,
            _ => MUTED,
        };
        rows.push(
            Row::new()
                .push(format!(" {}", cut(l, w as usize - 1)), fg(c))
                .done(),
        );
    }
    rows
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::model::DiffFile;
    use ratatui::Terminal;
    use ratatui::backend::TestBackend;

    fn screen(p: &Peek) -> (String, Vec<(Rect, PeekHit)>) {
        let (w, h) = (60, 20);
        let mut t = Terminal::new(TestBackend::new(w, h)).unwrap();
        let mut hits = vec![];
        t.draw(|f| hits = draw(f, p)).unwrap();
        let buf = t.backend().buffer().clone();
        let s = (0..h)
            .map(|y| {
                (0..w)
                    .map(|x| buf[(x, y)].symbol().to_string())
                    .collect::<String>()
            })
            .collect::<Vec<_>>()
            .join("\n");
        (s, hits)
    }

    fn peek() -> Peek {
        let mut p = Peek::new("%2".into());
        p.agent = Some(Agent {
            pane: "%2".into(),
            session: "notion-pilot".into(),
            state: "check".into(),
            task: Some("Refactor the OAuth wizard".into()),
            model: Some("Opus".into()),
            ctx: Some(61.0),
            ..Default::default()
        });
        p.output = "line 1\nline 2\n❯ Do you want to proceed?\n".into();
        p.diff = Some(Diff {
            files: vec![DiffFile {
                file: "src/wizard.py".into(),
                add: 42,
                del: 18,
            }],
            hunk: "@@ -1,2 +1,2 @@\n-old\n+new\n".into(),
        });
        p
    }

    #[test]
    fn output_tab() {
        let (s, hits) = screen(&peek());
        println!("{s}");
        for want in [
            "PEEK ◉ notion-pilot Refactor the OAuth wizard",
            "✕",
            "Output │ Diff +42 −18",
            "Opus · ctx 61%",
            "Do you want to proceed?",
            "dashboard stays open · ⇥ output/diff · esc close",
            "⏎ Go to agent",
        ] {
            assert!(s.contains(want), "missing {want:?}\n{s}");
        }
        assert!(hits.iter().any(|(_, h)| *h == PeekHit::Go));
        assert!(hits.iter().any(|(_, h)| *h == PeekHit::Close));
        assert!(hits.iter().any(|(_, h)| *h == PeekHit::Tab(PeekTab::Diff)));
    }

    #[test]
    fn diff_tab_and_keys() {
        let mut p = peek();
        assert_eq!(p.key(Key::Tab), PeekEffect::None);
        let (s, _) = screen(&p);
        assert!(
            s.contains("src/wizard.py")
                && s.contains("+42 −18")
                && s.contains("+new")
                && s.contains("@@ -1,2 +1,2 @@"),
            "{s}"
        );
        assert_eq!(p.key(Key::Enter), PeekEffect::GoTo("%2".into()));
        assert_eq!(p.key(Key::Esc), PeekEffect::Close);
    }
}
