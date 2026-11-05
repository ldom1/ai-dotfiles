//! Commandes tmux : aller à un agent, lui répondre, capturer son pane, ouvrir l'aperçu.

use std::process::Command;

use anyhow::{Context, Result};

use crate::model::Agent;

fn tmux(args: &[&str]) -> Result<String> {
    let out = Command::new("tmux")
        .args(args)
        .output()
        .context("run tmux")?;
    anyhow::ensure!(
        out.status.success(),
        "tmux {}: {}",
        args.join(" "),
        String::from_utf8_lossy(&out.stderr).trim()
    );
    Ok(String::from_utf8_lossy(&out.stdout).into_owned())
}

/// Amène le client tmux sur le pane de l'agent (session, fenêtre, pane).
pub fn go_to(pane: &str) -> Result<()> {
    tmux(&[
        "switch-client",
        "-t",
        pane,
        ";",
        "select-window",
        "-t",
        pane,
        ";",
        "select-pane",
        "-t",
        pane,
    ])
    .map(|_| ())
}

/// Touches tmux qui répondent à l'agent. `choice` : 1, 2, 3… ; `text` : réponse libre (touche i).
/// Claude Code : un chiffre choisit l'option affichée sous ce numéro et la valide.
/// Réponse libre : l'option qui suit les choix proposés (« Type something » pour une question,
/// « No, and tell Claude what to do differently » pour une permission), puis le texte et Entrée.
pub fn answer_keys(agent: &Agent, choice: Option<usize>, text: Option<&str>) -> Vec<Vec<String>> {
    let lit = |s: &str| vec!["-l".to_string(), s.to_string()];
    match (choice, text) {
        (Some(n), _) => vec![lit(&n.to_string())],
        (None, Some(t)) => {
            let free = if agent.is_permission() {
                3
            } else {
                agent.options.len() + 1
            };
            vec![lit(&free.to_string()), lit(t), vec!["Enter".into()]]
        }
        (None, None) => vec![],
    }
}

pub fn send(pane: &str, keys: &[Vec<String>]) -> Result<()> {
    for k in keys {
        let mut args = vec!["send-keys", "-t", pane];
        args.extend(k.iter().map(String::as_str));
        tmux(&args)?;
    }
    Ok(())
}

/// Interrompt le tour en cours de l'agent (Échap dans Claude Code).
pub fn interrupt(pane: &str) -> Result<()> {
    tmux(&["send-keys", "-t", pane, "Escape"]).map(|_| ())
}

/// Fin du buffer du pane : `lines` dernières lignes, lignes repliées rejointes.
pub fn capture(pane: &str, lines: usize) -> Result<String> {
    let start = format!("-{lines}");
    tmux(&["capture-pane", "-p", "-J", "-t", pane, "-S", &start])
}

/// Aperçu dans un popup à droite (≈ 40 % de la fenêtre) : le pane courant reste visible.
pub fn open_peek(pane: &str) -> Result<()> {
    let exe = std::env::current_exe().context("current exe")?;
    let cmd = format!("'{}' peek '{}'", exe.display(), pane);
    tmux(&[
        "display-popup",
        "-x",
        "R",
        "-y",
        "0",
        "-w",
        "40%",
        "-h",
        "100%",
        "-E",
        &cmd,
    ])
    .map(|_| ())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn agent(options: &[&str]) -> Agent {
        Agent {
            options: options.iter().map(|s| s.to_string()).collect(),
            ..Default::default()
        }
    }

    #[test]
    fn digit_answers_the_option() {
        assert_eq!(
            answer_keys(&agent(&["a", "b"]), Some(2), None),
            vec![vec!["-l", "2"]]
        );
    }

    #[test]
    fn free_reply_on_a_question_picks_the_option_after_the_choices() {
        let k = answer_keys(&agent(&["pdfplumber", "PyMuPDF"]), None, Some("use pypdf"));
        assert_eq!(
            k,
            vec![vec!["-l", "3"], vec!["-l", "use pypdf"], vec!["Enter"]]
        );
    }

    #[test]
    fn free_reply_on_a_permission_says_no_with_a_reason() {
        let k = answer_keys(&agent(&["Yes", "Always", "No"]), None, Some("not now"));
        assert_eq!(k[0], vec!["-l", "3"]);
    }
}
