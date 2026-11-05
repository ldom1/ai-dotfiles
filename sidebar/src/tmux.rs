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
/// Vérifié dans Claude Code 2.1.318 (claude --model haiku dans un serveur tmux de test) :
/// - question (AskUserQuestion) : un chiffre choisit l'option et valide ; l'option qui suit les
///   choix est « Type something » : son chiffre place le curseur dessus, le texte s'y écrit, Entrée envoie ;
/// - permission : 1 « Yes », 2 « Yes, and always allow… » ; le menu a 3 ou 4 options et la 3 peut
///   être « switch to auto mode » : « No » est donc Échap, qui refuse l'outil et attend un prompt.
///   Réponse libre : Échap, puis le texte envoyé comme prompt.
pub fn answer_keys(agent: &Agent, choice: Option<usize>, text: Option<&str>) -> Vec<Vec<String>> {
    let lit = |s: &str| vec!["-l".to_string(), s.to_string()];
    let key = |s: &str| vec![s.to_string()];
    let perm = agent.is_permission();
    match (choice, text) {
        (Some(3), _) if perm => vec![key("Escape")],
        (Some(n), _) => vec![lit(&n.to_string())],
        (None, Some(t)) if perm => vec![key("Escape"), lit(t), key("Enter")],
        (None, Some(t)) => vec![
            lit(&(agent.options.len() + 1).to_string()),
            lit(t),
            key("Enter"),
        ],
        (None, None) => vec![],
    }
}

/// Envoie les touches une par une ; pause entre deux envois, le temps que Claude Code
/// ferme le menu ou ouvre le champ de texte.
pub fn send(pane: &str, keys: &[Vec<String>]) -> Result<()> {
    for (i, k) in keys.iter().enumerate() {
        if i > 0 {
            std::thread::sleep(std::time::Duration::from_millis(300));
        }
        let mut args = vec!["send-keys", "-t", pane];
        args.extend(k.iter().map(String::as_str));
        tmux(&args)?;
    }
    Ok(())
}

fn run(args: &[&str]) -> Result<()> {
    tmux(args).map(|_| ())
}

/// Script de tmux-resurrect (`save.sh quiet` ou `restore.sh`), lancé et attendu.
fn resurrect(script: &str, args: &[&str]) -> Result<()> {
    let home = std::env::var("HOME").unwrap_or_default();
    let path = format!("{home}/.tmux/plugins/tmux-resurrect/scripts/{script}");
    let st = Command::new(&path)
        .args(args)
        .status()
        .with_context(|| format!("run {path}"))?;
    anyhow::ensure!(st.success(), "{script} failed");
    Ok(())
}

pub fn save() -> Result<()> {
    resurrect("save.sh", &["quiet"])
}

pub fn restore() -> Result<()> {
    resurrect("restore.sh", &[])
}

pub fn switch(name: &str) -> Result<()> {
    run(&["switch-client", "-t", &format!("={name}")])
}

/// Crée la session (sans la lier au terminal), puis y amène le client.
pub fn create(name: &str, dir: &str) -> Result<()> {
    run(&["new-session", "-d", "-s", name, "-c", dir])?;
    switch(name)
}

/// Sauvegarde d'abord (la session ne revient pas à la restauration), puis tue la session.
pub fn kill_session(name: &str) -> Result<()> {
    save()?;
    run(&["kill-session", "-t", &format!("={name}")])
}

pub fn save_exit() -> Result<()> {
    save()?;
    run(&["kill-server"])
}

pub fn detach() -> Result<()> {
    run(&["detach-client"])
}

pub fn rename(from: &str, to: &str) -> Result<()> {
    run(&["rename-session", "-t", &format!("={from}"), to])
}

pub fn last_session() -> Result<()> {
    run(&["switch-client", "-l"])
}

/// Split ou zoom du pane de travail : le dernier pane actif de la fenêtre (« ! »), pas la sidebar.
pub fn split(right: bool) -> Result<()> {
    run(&[
        "split-window",
        if right { "-h" } else { "-v" },
        "-t",
        "!",
        "-c",
        "#{pane_current_path}",
    ])
}

pub fn zoom() -> Result<()> {
    run(&["resize-pane", "-Z", "-t", "!"])
}

/// Atténue (ou rétablit) le pane de travail pendant un écran de confirmation.
pub fn dim(on: bool) {
    let _ = if on {
        run(&["set", "-p", "-t", "!", "window-style", "fg=#5c6370"])
    } else {
        run(&["set", "-pu", "-t", "!", "window-style"])
    };
}

pub fn toggle_sidebar() -> Result<()> {
    let repo = std::env::var("AIF_DOTFILES")
        .unwrap_or_else(|_| format!("{}/ai-dotfiles", std::env::var("HOME").unwrap_or_default()));
    let st = Command::new("sh")
        .arg(format!("{repo}/config/tmux-sidebar.sh"))
        .arg("toggle")
        .status()
        .context("run tmux-sidebar.sh")?;
    anyhow::ensure!(st.success(), "tmux-sidebar.sh toggle failed");
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
    fn permission_no_is_escape_because_option_3_may_switch_to_auto_mode() {
        let p = agent(&["Yes", "Always", "No"]);
        assert_eq!(answer_keys(&p, Some(1), None), vec![vec!["-l", "1"]]);
        assert_eq!(answer_keys(&p, Some(3), None), vec![vec!["Escape"]]);
    }

    #[test]
    fn free_reply_on_a_permission_refuses_then_prompts() {
        let k = answer_keys(&agent(&["Yes", "Always", "No"]), None, Some("not now"));
        assert_eq!(
            k,
            vec![vec!["Escape"], vec!["-l", "not now"], vec!["Enter"]]
        );
    }
}
