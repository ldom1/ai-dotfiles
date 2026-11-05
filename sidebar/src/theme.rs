//! Palette et glyphes de la spécification (6.1, 6.2). Un glyphe = une colonne.

use ratatui::style::{Color, Modifier, Style};

pub const BG: Color = Color::Rgb(0x0E, 0x0F, 0x13);
pub const SELECTED: Color = Color::Rgb(0x1A, 0x1D, 0x26);
pub const LINE: Color = Color::Rgb(0x23, 0x26, 0x2F);
pub const TREE: Color = Color::Rgb(0x3B, 0x40, 0x50);
pub const ACCENT: Color = Color::Rgb(0xBB, 0x9A, 0xF7);
pub const TEXT: Color = Color::Rgb(0xD8, 0xDC, 0xE6);
pub const MUTED: Color = Color::Rgb(0x8A, 0x90, 0xA0);
pub const GIT: Color = Color::Rgb(0x73, 0xDA, 0xCA);
pub const CHECK: Color = Color::Rgb(0xFF, 0x9E, 0x64);
pub const RUNNING: Color = Color::Rgb(0x7A, 0xA2, 0xF7);
pub const DONE: Color = Color::Rgb(0x9E, 0xCE, 0x6A);
pub const ERROR: Color = Color::Rgb(0xF7, 0x76, 0x8E);

pub const SPINNER: [&str; 10] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

pub fn fg(c: Color) -> Style {
    Style::new().fg(c)
}

pub fn bold(c: Color) -> Style {
    Style::new().fg(c).add_modifier(Modifier::BOLD)
}

/// Glyphe d'état ; `tick` anime le spinner de running.
pub fn glyph(state: &str, tick: usize) -> &'static str {
    match state {
        "check" => "◉",
        "running" => SPINNER[tick % SPINNER.len()],
        "done" => "✓",
        "stale" => "◌",
        "error" => "✕",
        _ => "?",
    }
}

pub fn state_color(state: &str) -> Color {
    match state {
        "check" => CHECK,
        "running" => RUNNING,
        "done" => DONE,
        "error" => ERROR,
        _ => MUTED,
    }
}

/// Titre de section de l'onglet AGENTS.
pub fn section_title(state: &str) -> &'static str {
    match state {
        "check" => "TO CHECK",
        "error" => "ERROR",
        "done" => "DONE",
        "running" => "RUNNING",
        "stale" => "STALE",
        _ => "UNKNOWN",
    }
}

/// Barre de contexte de 10 cellules : ▰▰▰▰▰▰▱▱▱▱
pub fn ctx_bar(pct: f64) -> String {
    let full = ((pct.clamp(0.0, 100.0) / 10.0).round()) as usize;
    "▰".repeat(full) + &"▱".repeat(10 - full)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bar() {
        assert_eq!(ctx_bar(61.0), "▰▰▰▰▰▰▱▱▱▱");
        assert_eq!(ctx_bar(0.0), "▱▱▱▱▱▱▱▱▱▱");
        assert_eq!(ctx_bar(150.0), "▰▰▰▰▰▰▰▰▰▰");
    }

    #[test]
    fn glyphs() {
        assert_eq!(glyph("check", 0), "◉");
        assert_eq!(glyph("running", 2), "⠹");
        assert_eq!(glyph("whatever", 0), "?");
    }
}
