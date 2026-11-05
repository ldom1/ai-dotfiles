//! Sessions tmux, nom d'une nouvelle session, dossiers proposés, dernière sauvegarde.

use std::path::Path;
use std::process::Command;

#[derive(Debug, Clone, Default, PartialEq)]
pub struct Session {
    pub name: String,
    pub path: String,
}

fn tmux_out(args: &[&str]) -> Option<String> {
    let out = Command::new("tmux").args(args).output().ok()?;
    out.status
        .success()
        .then(|| String::from_utf8_lossy(&out.stdout).into_owned())
}

/// Sessions tmux. Séparateur imprimable : tmux ≥ 3.3 remplace la tabulation par « _ ».
pub fn load_sessions() -> Vec<Session> {
    let out =
        tmux_out(&["list-sessions", "-F", "#{session_name}|:|#{session_path}"]).unwrap_or_default();
    parse_sessions(&out)
}

pub fn parse_sessions(out: &str) -> Vec<Session> {
    out.lines()
        .filter_map(|l| l.split_once("|:|"))
        .map(|(n, p)| Session {
            name: n.into(),
            path: p.into(),
        })
        .collect()
}

/// Session du pane de la sidebar (la session courante pour l'utilisateur).
pub fn current_session() -> String {
    let pane = std::env::var("TMUX_PANE").unwrap_or_default();
    let mut args = vec!["display", "-p"];
    if !pane.is_empty() {
        args.extend(["-t", pane.as_str()]);
    }
    args.push("#{session_name}");
    tmux_out(&args)
        .map(|s| s.trim().to_string())
        .unwrap_or_default()
}

pub fn home() -> String {
    std::env::var("HOME").unwrap_or_default()
}

/// « ~/… » à la place du dossier personnel.
pub fn tilde(path: &str, home: &str) -> String {
    match path.strip_prefix(home) {
        Some(rest) if !home.is_empty() && (rest.is_empty() || rest.starts_with('/')) => {
            format!("~{rest}")
        }
        _ => path.to_string(),
    }
}

/// Nom de session d'un dossier : son nom (`main` pour ~), « . » et « : » remplacés (règle de `tma`).
pub fn base_name(dir: &str, home: &str) -> String {
    if dir == home {
        return "main".into();
    }
    let b = Path::new(dir)
        .file_name()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or_else(|| dir.into());
    b.replace(['.', ':'], "_")
}

/// Ce que la création d'une session pour ce dossier donnerait.
#[derive(Debug, Clone, PartialEq)]
pub enum Fit {
    /// Nom libre : nouvelle session
    New(String),
    /// Une session est déjà ouverte sur ce dossier : s'y attacher
    Attach(String),
    /// Nom pris par une session d'un autre dossier : suffixe -2, -3… (règle de tmux-name-session.sh)
    Taken { by: String, name: String },
}

impl Fit {
    pub fn name(&self) -> &str {
        match self {
            Fit::New(n) | Fit::Attach(n) | Fit::Taken { name: n, .. } => n,
        }
    }
}

pub fn fit(dir: &str, home: &str, sessions: &[Session]) -> Fit {
    if let Some(s) = sessions.iter().find(|s| s.path == dir) {
        return Fit::Attach(s.name.clone());
    }
    let base = base_name(dir, home);
    let Some(owner) = sessions.iter().find(|s| s.name == base) else {
        return Fit::New(base);
    };
    let taken = |n: &str| sessions.iter().any(|s| s.name == n);
    let name = (2..)
        .map(|i| format!("{base}-{i}"))
        .find(|n| !taken(n))
        .unwrap();
    Fit::Taken {
        by: owner.path.clone(),
        name,
    }
}

/// Dossiers proposés pour une nouvelle session : zoxide s'il est installé, sinon les dépôts git
/// sous ~ (3 niveaux, dossiers cachés et dossiers de build ignorés).
pub fn folders(home: &str) -> Vec<String> {
    if let Some(out) = Command::new("zoxide")
        .args(["query", "-l"])
        .output()
        .ok()
        .filter(|o| o.status.success())
    {
        let v: Vec<String> = String::from_utf8_lossy(&out.stdout)
            .lines()
            .map(str::to_string)
            .collect();
        if !v.is_empty() {
            return v;
        }
    }
    let mut found = vec![home.to_string()];
    walk(Path::new(home), 3, &mut found);
    found.sort();
    found.dedup();
    found
}

fn walk(dir: &Path, depth: u8, found: &mut Vec<String>) {
    let Ok(entries) = std::fs::read_dir(dir) else {
        return;
    };
    for e in entries.flatten() {
        let name = e.file_name().to_string_lossy().into_owned();
        if name.starts_with('.')
            || ["node_modules", "target", "venv", "__pycache__"].contains(&name.as_str())
        {
            continue;
        }
        let p = e.path();
        if !e.file_type().is_ok_and(|t| t.is_dir()) {
            continue;
        }
        if p.join(".git").exists() {
            found.push(p.to_string_lossy().into_owned());
        } else if depth > 1 {
            walk(&p, depth - 1, found);
        }
    }
}

/// Heure (s) de la dernière sauvegarde tmux-resurrect : fichier `last` de son dossier.
pub fn last_save() -> Option<i64> {
    let home = home();
    let dir = tmux_out(&["show", "-gqv", "@resurrect-dir"])
        .map(|s| s.trim().replace('~', &home))
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| {
            let old = format!("{home}/.tmux/resurrect");
            if Path::new(&old).is_dir() {
                old
            } else {
                format!("{home}/.local/share/tmux/resurrect")
            }
        });
    let m = std::fs::metadata(format!("{dir}/last"))
        .ok()?
        .modified()
        .ok()?;
    Some(m.duration_since(std::time::UNIX_EPOCH).ok()?.as_secs() as i64)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn s(name: &str, path: &str) -> Session {
        Session {
            name: name.into(),
            path: path.into(),
        }
    }

    #[test]
    fn names_follow_tma() {
        assert_eq!(base_name("/home/l", "/home/l"), "main");
        assert_eq!(base_name("/home/l/dev/my.app", "/home/l"), "my_app");
        assert_eq!(tilde("/home/l/dev/x", "/home/l"), "~/dev/x");
        assert_eq!(tilde("/home/lx", "/home/l"), "/home/lx");
    }

    #[test]
    fn fit_new_attach_taken() {
        let sessions = vec![
            s("api", "/w/a/api"),
            s("api-2", "/w/b/api"),
            s("main", "/h"),
        ];
        assert_eq!(fit("/w/c/web", "/h", &sessions), Fit::New("web".into()));
        assert_eq!(
            fit("/w/b/api", "/h", &sessions),
            Fit::Attach("api-2".into())
        );
        assert_eq!(
            fit("/w/c/api", "/h", &sessions),
            Fit::Taken {
                by: "/w/a/api".into(),
                name: "api-3".into()
            }
        );
        assert_eq!(fit("/h", "/h", &sessions), Fit::Attach("main".into()));
    }

    #[test]
    fn parses_list_sessions() {
        assert_eq!(
            parse_sessions("a|:|/x\nb|:|/y z\n"),
            vec![s("a", "/x"), s("b", "/y z")]
        );
    }
}
