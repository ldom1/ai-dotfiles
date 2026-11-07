//! Vue d'aide (popup centré) : 4 colonnes de raccourcis, légende des glyphes.
//! Ouverte par la case « ? » de la sidebar, « ? help » en pied, la touche « ? » et `prefix ?`.

use ratatui::Frame;
use ratatui::layout::Rect;
use ratatui::style::Style;
use ratatui::widgets::{Block, Paragraph};

use crate::theme::*;
use crate::ui::{Row, cut};

type Section = (&'static str, &'static [(&'static str, &'static str)]);

/// Raccourcis réellement en place (tmux.conf, aif-sidebar).
pub const SECTIONS: [Section; 4] = [
    (
        "NAVIGATE",
        &[
            ("↑↓ · j k", "move"),
            ("1–9", "jump to agent"),
            ("/", "filter"),
            ("o", "change sort"),
            ("⇥", "next tab"),
            ("?", "help"),
            ("click", "rows and keys shown"),
            ("space · ▾", "fold section"),
        ],
    ),
    (
        "AGENTS",
        &[
            ("⏎", "go to agent"),
            ("p", "peek"),
            ("⇥", "output/diff in peek"),
            ("1 2 3", "answer"),
            ("i", "reply"),
            ("x", "interrupt"),
        ],
    ),
    (
        "SESSIONS",
        &[
            ("T", "new terminal (~)"),
            ("⌃⇧N", "new"),
            ("+ · prefix +", "new project"),
            ("r", "rename"),
            ("prefix ⇥", "last session"),
            ("s", "save now"),
            ("d", "exit (detach)"),
            ("prefix Q", "save & exit"),
            ("⌃⇧K", "kill session"),
        ],
    ),
    (
        "PANES & VIEW",
        &[
            ("⌃⇧O", "split right"),
            ("⌃⇧E", "split below"),
            ("⌃⇧X", "close pane"),
            ("⌥ arrows", "move"),
            ("⌥Z", "zoom"),
            ("⌃⇧B", "hide sidebar"),
            ("⌥S", "focus sidebar"),
            ("right-click", "sidebar menu"),
            ("prefix /", "tmux keys"),
        ],
    ),
];

const LEGEND: [(&str, &str, &str); 6] = [
    ("check", "◉", "to check"),
    ("running", "⠹", "running"),
    ("done", "✓", "done"),
    ("stale", "◌", "stale"),
    ("error", "✕", "error"),
    ("unknown", "?", "unknown"),
];

/// Colonnes selon la largeur : 4, 2 ou 1.
pub fn columns(w: u16) -> usize {
    match w {
        120.. => 4,
        48..=119 => 2,
        _ => 1,
    }
}

/// Lignes de l'aide pour une largeur donnée.
pub fn rows(w: u16) -> Vec<Row<()>> {
    let cols = columns(w);
    let cell = (w as usize).saturating_sub(2) / cols;
    let key_w = 11.min(cell / 2);
    let mut rows = vec![Row::new().push(" KEYS", bold(ACCENT)).done(), Row::new()];
    for group in SECTIONS.chunks(cols) {
        let height = group.iter().map(|(_, k)| k.len() + 1).max().unwrap_or(0);
        for line in 0..height {
            let mut r = Row::new();
            r.push(" ", Style::new());
            for (title, keys) in group {
                let used = r.width();
                if line == 0 {
                    r.push(cut(title, cell - 1), bold(MUTED));
                } else if let Some((k, d)) = keys.get(line - 1) {
                    let k = cut(k, key_w);
                    r.push(format!("{k:<key_w$}"), fg(ACCENT));
                    r.push(
                        format!(" {}", cut(d, cell.saturating_sub(key_w + 2))),
                        fg(TEXT),
                    );
                }
                let pad = (cell as u16).saturating_sub(r.width() - used);
                r.push(" ".repeat(pad as usize), Style::new());
            }
            rows.push(r);
        }
        rows.push(Row::new());
    }
    // Légende des glyphes, renvoyée à la ligne si besoin
    let mut r = Row::new();
    r.push(" ", Style::new());
    for (state, g, label) in LEGEND {
        let len = (g.chars().count() + label.len() + 3) as u16;
        if r.width() + len > w && r.width() > 1 {
            rows.push(std::mem::take(&mut r));
            r.push(" ", Style::new());
        }
        r.push(g, fg(state_color(state)))
            .push(format!(" {label}   "), fg(MUTED));
    }
    rows.push(r);
    rows
}

pub fn draw(f: &mut Frame) {
    let area = f.area();
    f.render_widget(Block::new().style(Style::new().bg(BG).fg(TEXT)), area);
    let w = area.width;
    let mut y = area.y;
    for r in rows(w).iter().take(area.height.saturating_sub(1) as usize) {
        f.render_widget(
            Paragraph::new(r.line(w)),
            Rect {
                x: area.x,
                y,
                width: w,
                height: 1,
            },
        );
        y += 1;
    }
    let mut foot: Row<()> = Row::new();
    foot.right("esc close ", fg(MUTED), w);
    f.render_widget(
        Paragraph::new(foot.line(w)),
        Rect {
            x: area.x,
            y: area.bottom().saturating_sub(1),
            width: w,
            height: 1,
        },
    );
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::Terminal;
    use ratatui::backend::TestBackend;

    fn screen(w: u16, h: u16) -> String {
        let mut t = Terminal::new(TestBackend::new(w, h)).unwrap();
        t.draw(draw).unwrap();
        let buf = t.backend().buffer().clone();
        (0..h)
            .map(|y| {
                (0..w)
                    .map(|x| buf[(x, y)].symbol().to_string())
                    .collect::<String>()
            })
            .collect::<Vec<_>>()
            .join("\n")
    }

    #[test]
    fn four_columns_with_every_section_and_the_legend() {
        let s = screen(130, 20);
        println!("{s}");
        let title_line = s.lines().find(|l| l.contains("NAVIGATE")).unwrap();
        for t in ["NAVIGATE", "AGENTS", "SESSIONS", "PANES & VIEW"] {
            assert!(title_line.contains(t), "{t} not on the title line\n{s}");
        }
        for want in [
            "1–9",
            "jump to agent",
            "1 2 3",
            "answer",
            "prefix Q",
            "save & exit",
            "⌃⇧K",
            "kill session",
            "right-click",
            "sidebar menu",
            "◉ to check",
            "⠹ running",
            "? unknown",
            "esc close",
        ] {
            assert!(s.contains(want), "missing {want:?}\n{s}");
        }
    }

    #[test]
    fn narrow_popup_uses_two_then_one_column() {
        assert_eq!(columns(130), 4);
        assert_eq!(columns(70), 2);
        assert_eq!(columns(40), 1);
        let s = screen(70, 40);
        println!("{s}");
        assert!(
            s.lines()
                .any(|l| l.contains("NAVIGATE") && l.contains("AGENTS")),
            "{s}"
        );
        assert!(s.contains("PANES & VIEW") && s.contains("tmux keys"), "{s}");
    }
}
