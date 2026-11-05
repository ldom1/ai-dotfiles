//! Données : sortie de `aif-agents list --json` et `aif-agents diff <pane> --json`.
//! Les vues ne lisent rien d'autre (avec tmux).

use std::collections::BTreeMap;
use std::process::Command;

use anyhow::{Context, Result};
use serde::Deserialize;

#[derive(Debug, Clone, Default, Deserialize, PartialEq)]
pub struct Git {
    #[serde(default)]
    pub add: u64,
    #[serde(default)]
    pub del: u64,
    #[serde(default)]
    pub files: u64,
}

#[derive(Debug, Clone, Default, Deserialize, PartialEq)]
pub struct Subagent {
    #[serde(rename = "type", default)]
    pub kind: String,
    #[serde(default)]
    pub state: String,
}

#[derive(Debug, Clone, Default, Deserialize, PartialEq)]
pub struct Agent {
    pub pane: String,
    #[serde(default)]
    pub session: String,
    #[serde(default)]
    pub cwd: Option<String>,
    #[serde(default)]
    pub state: String,
    #[serde(default)]
    pub tool: Option<String>,
    #[serde(default)]
    pub task: Option<String>,
    #[serde(default)]
    pub question: Option<String>,
    #[serde(default)]
    pub options: Vec<String>,
    #[serde(default)]
    pub last_tool: Option<String>,
    #[serde(default)]
    pub subagents: BTreeMap<String, Subagent>,
    #[serde(default)]
    pub model: Option<String>,
    #[serde(default)]
    pub ctx: Option<f64>,
    #[serde(default)]
    pub updated_at: Option<i64>,
    #[serde(default)]
    pub started_at: Option<i64>,
    /// Heure du dernier prompt (UserPromptSubmit) : durée affichée d'un agent running.
    #[serde(default)]
    pub prompt_at: Option<i64>,
    #[serde(default)]
    pub error: Option<String>,
    #[serde(default)]
    pub jump: Option<u8>,
    #[serde(default)]
    pub git: Option<Git>,
}

impl Agent {
    pub fn tool_name(&self) -> &str {
        self.tool.as_deref().unwrap_or("claude")
    }

    /// Demande de permission (options Yes / Always / No posées par le hook) ou question.
    pub fn is_permission(&self) -> bool {
        self.options == ["Yes", "Always", "No"]
    }

    /// Texte des champs filtrables : session, tâche, question, dossier, outil.
    pub fn haystack(&self) -> String {
        [
            Some(self.session.as_str()),
            self.task.as_deref(),
            self.question.as_deref(),
            self.cwd.as_deref(),
            Some(self.tool_name()),
        ]
        .into_iter()
        .flatten()
        .collect::<Vec<_>>()
        .join(" ")
        .to_lowercase()
    }
}

#[derive(Debug, Clone, Default, Deserialize, PartialEq)]
pub struct DiffFile {
    pub file: String,
    #[serde(default)]
    pub add: u64,
    #[serde(default)]
    pub del: u64,
}

#[derive(Debug, Clone, Default, Deserialize, PartialEq)]
pub struct Diff {
    #[serde(default)]
    pub files: Vec<DiffFile>,
    #[serde(default)]
    pub hunk: String,
}

fn aif_agents(args: &[&str]) -> Result<Vec<u8>> {
    let bin = std::env::var("AIF_AGENTS_BIN").unwrap_or_else(|_| "aif-agents".into());
    let out = Command::new(&bin)
        .args(args)
        .output()
        .with_context(|| format!("run {bin}"))?;
    anyhow::ensure!(
        out.status.success(),
        "{bin} {}: {}",
        args.join(" "),
        String::from_utf8_lossy(&out.stderr)
    );
    Ok(out.stdout)
}

pub fn load_agents() -> Result<Vec<Agent>> {
    parse_agents(&aif_agents(&["list", "--json"])?)
}

pub fn parse_agents(json: &[u8]) -> Result<Vec<Agent>> {
    Ok(serde_json::from_slice(json)?)
}

pub fn load_diff(pane: &str) -> Result<Diff> {
    Ok(serde_json::from_slice(&aif_agents(&[
        "diff", pane, "--json",
    ])?)?)
}

/// Durée courte : « 12 s », « 14 min », « 2 h 10 », « 3 d ».
pub fn ago(now: i64, then: Option<i64>) -> String {
    let Some(then) = then else {
        return String::new();
    };
    let s = (now - then).max(0);
    match s {
        0..=59 => format!("{s} s"),
        60..=3599 => format!("{} min", s / 60),
        3600..=86_399 => format!("{} h {:02}", s / 3600, (s % 3600) / 60),
        _ => format!("{} d", s / 86_400),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_aif_agents_output() {
        let json = br#"[{"tool":"claude","state":"check","pane":"%3","session":"prosper","cwd":"/p",
            "task":"Parse","question":"Which parser?","options":["pdfplumber","PyMuPDF"],
            "subagents":{"ag1":{"type":"Explore","state":"running","since":1}},
            "model":"Opus","ctx":61,"updated_at":10,"jump":1,"git":{"add":42,"del":18,"files":3}},
            {"pane":"%4","session":"x","state":"unknown","cwd":"/x","tool":"claude","git":null,"jump":2}]"#;
        let a = parse_agents(json).unwrap();
        assert_eq!(a.len(), 2);
        assert_eq!(a[0].options, ["pdfplumber", "PyMuPDF"]);
        assert_eq!(a[0].subagents["ag1"].kind, "Explore");
        assert_eq!(
            a[0].git,
            Some(Git {
                add: 42,
                del: 18,
                files: 3
            })
        );
        assert_eq!(a[1].git, None);
        assert!(!a[0].is_permission());
        assert!(a[0].haystack().contains("which parser?"));
    }

    #[test]
    fn durations() {
        assert_eq!(ago(100, Some(88)), "12 s");
        assert_eq!(ago(1000, Some(1000 - 14 * 60)), "14 min");
        assert_eq!(ago(10_000, Some(10_000 - 7800)), "2 h 10");
        assert_eq!(ago(0, None), "");
    }
}
