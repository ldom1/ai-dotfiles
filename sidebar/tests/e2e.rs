//! Tests de bout en bout « à la Playwright » : un vrai client tmux tourne dans un terminal émulé
//! (tui-test, Microsoft), avec config/tmux.conf, tmux-sidebar.sh et ce aif-sidebar. Les tests
//! cliquent et tapent comme l'utilisateur, puis lisent l'état tmux.
//!
//! Isolation : chaque test a son propre dossier sous /tmp. Il sert de HOME et de TMUX_TMPDIR, et
//! TMUX est retiré de l'environnement. Tout `tmux` lancé ici, par le test, la config, les hooks
//! ou la sidebar, parle donc au serveur du test, jamais aux sessions de l'utilisateur.
//!
//! Lancer : cargo test --test e2e

use std::os::unix::fs::symlink;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{Duration, Instant};

use tempfile::TempDir;
use tui_test::{
    LocatorExpectOptions, MouseAction, MouseOptions, OpenOptions, Operation, OperationResult,
    RunOptions,
    Session,
};

const COLS: u16 = 160;
const ROWS: u16 = 40;

struct Env {
    // Gardé jusqu'à la fin du test : le dossier disparaît avec lui.
    dir: TempDir,
    term: Session,
}

impl Env {
    fn home(&self) -> PathBuf {
        self.dir.path().join("h")
    }

    /// Variables de tout process lancé par le test : HOME et TMUX_TMPDIR du test.
    fn vars(&self) -> Vec<(String, String)> {
        let repo = repo();
        let path = format!(
            "{}:{}",
            self.dir.path().join("bin").display(),
            std::env::var("PATH").unwrap_or_default()
        );
        vec![
            ("HOME".into(), self.home().display().to_string()),
            ("TMUX_TMPDIR".into(), self.dir.path().display().to_string()),
            ("PATH".into(), path),
            ("AIF_PLATFORM".into(), "linux".into()),
            ("AIF_DOTFILES".into(), repo.display().to_string()),
            (
                "AIF_STATE_DIR".into(),
                self.dir.path().join("agents").display().to_string(),
            ),
            ("TERM".into(), "xterm-256color".into()),
            ("SHELL".into(), "/bin/sh".into()),
        ]
    }

    /// tmux sur le serveur du test (jamais celui de l'utilisateur).
    fn tmux(&self, args: &[&str]) -> String {
        let out = Command::new("tmux")
            .args(args)
            .env_remove("TMUX")
            .env_remove("TMUX_PANE")
            .env_remove("_ZO_DATA_DIR")
            .envs(self.vars())
            .output()
            .expect("tmux");
        String::from_utf8_lossy(&out.stdout).trim().to_string()
    }

    /// Démarre un client tmux attaché, dans le terminal émulé, et attend la sidebar.
    fn start() -> Env {
        let dir = tempfile::Builder::new()
            .prefix("aif-e2e")
            .tempdir_in("/tmp") // chemin court : un socket tmux tient en 108 octets
            .unwrap();
        let env = Env {
            term: Session::new(dir.path().file_name().unwrap().to_string_lossy()),
            dir,
        };
        let (h, d) = (env.home(), env.dir.path());
        let r = resurrect(&h);
        for p in [
            h.join(".tmux/plugins/tpm"),
            h.join(".local/bin"),
            r.clone(),
            h.join("dev/web/.git"),
            h.join("lab/site/.git"),
            h.join("lab/blog/.git"),
            d.join("bin"),
            d.join("agents"),
        ] {
            std::fs::create_dir_all(p).unwrap();
        }
        symlink(repo(), h.join("ai-dotfiles")).unwrap();
        symlink(repo().join("config/tmux.conf"), h.join(".tmux.conf")).unwrap();
        // Une copie, comme une installation : un test peut la remplacer comme le fait cargo build
        std::fs::copy(env!("CARGO_BIN_EXE_aif-sidebar"), d.join("aif-sidebar")).unwrap();
        symlink(d.join("aif-sidebar"), h.join(".local/bin/aif-sidebar")).unwrap();
        symlink(repo().join("bin/aif-agents"), d.join("bin/aif-agents")).unwrap();
        script(&h.join(".tmux/plugins/tpm/tpm"), "#!/bin/sh\n");
        script(
            &r.join("save.sh"),
            "#!/bin/sh\nd=\"$HOME/.local/share/tmux/resurrect\"; mkdir -p \"$d\"; touch \"$d/last\"\n",
        );
        // Pas de zoxide : les dossiers proposés sont les dépôts git sous ~
        script(&d.join("bin/zoxide"), "#!/bin/sh\nexit 1\n");
        // Faux agent : écrit les touches reçues dans keys
        script(
            &d.join("bin/claude"),
            "#!/bin/sh\nstty raw -echo\ncat > \"$HOME/../keys\"\n",
        );

        let mut args = vec!["-u".into(), "TMUX".into(), "-u".into(), "TMUX_PANE".into()];
        args.extend(env.vars().iter().map(|(k, v)| format!("{k}={v}")));
        args.extend(
            ["tmux", "new-session", "-s", "main", "-c"]
                .map(String::from)
                .into_iter()
                .chain([h.display().to_string()]),
        );
        let o = OpenOptions::default();
        env.term
            .run(RunOptions {
                backend: o.backend,
                program: "env".into(),
                args,
                profile: o.profile,
                style: o.style,
                cols: COLS,
                rows: ROWS,
                cwd: Some(h.display().to_string()),
                env: vec![],
                wait_ready: Some(false),
                restart: false,
                timeouts: o.timeouts,
                recording: o.recording,
            })
            .unwrap();
        env.expect("SESSIONS 1"); // sessions chargées (rafraîchies toutes les secondes)
        env
    }

    fn expect(&self, text: &str) {
        self.term
            .get_by_text(text)
            .first()
            .expect_with(LocatorExpectOptions {
                timeout_ms: Some(5000),
                ..Default::default()
            })
            .unwrap_or_else(|e| panic!("« {text} » absent : {e}\n{}", self.screen()));
    }

    fn screen(&self) -> String {
        match self.term.execute(Operation::Text { full: false }) {
            Ok(OperationResult::Text(t)) => t,
            other => format!("{other:?}"),
        }
    }

    /// Clic gauche sur une cellule (0-indexée).
    fn click_at(&self, x: u16, y: u16) {
        self.term
            .execute(Operation::Mouse {
                action: MouseAction::Click {
                    x: Some(x),
                    y: Some(y),
                    on_text: None,
                    options: MouseOptions::default(),
                    clicks: 1,
                },
            })
            .unwrap();
    }

    /// Clic au milieu d'un texte visible.
    fn click(&self, text: &str) {
        self.expect(text);
        self.term.get_by_text(text).first().click().unwrap();
    }

    /// Ligne (y) d'un texte visible.
    fn row_of(&self, text: &str) -> u16 {
        self.expect(text);
        self.term.get_by_text(text).first().location().unwrap().start.row as u16
    }

    fn type_text(&self, s: &str) {
        self.term
            .execute(Operation::Write { data: s.into() })
            .unwrap();
    }

    /// Attend qu'une commande tmux renvoie `want`.
    fn wait_tmux(&self, args: &[&str], want: &str) {
        let start = Instant::now();
        while start.elapsed() < Duration::from_secs(5) {
            if self.tmux(args) == want {
                return;
            }
            std::thread::sleep(Duration::from_millis(100));
        }
        panic!(
            "tmux {args:?} = « {} », attendu « {want} »\n{}",
            self.tmux(args),
            self.screen()
        );
    }

    fn client_session(&self) -> String {
        self.tmux(&["list-clients", "-F", "#{client_session}"])
    }
}

impl Drop for Env {
    fn drop(&mut self) {
        self.term.close().ok();
        self.tmux(&["kill-server"]);
    }
}

fn repo() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap().to_path_buf()
}

fn resurrect(home: &Path) -> PathBuf {
    home.join(".tmux/plugins/tmux-resurrect/scripts")
}

fn script(p: &Path, body: &str) {
    use std::os::unix::fs::PermissionsExt;
    std::fs::write(p, body).unwrap();
    std::fs::set_permissions(p, std::fs::Permissions::from_mode(0o755)).unwrap();
}

#[test]
fn harness_runs_on_its_own_server_and_clicks_a_tab() {
    let e = Env::start();
    let sock = e.tmux(&["display", "-p", "#{socket_path}"]);
    assert!(
        sock.starts_with(&e.dir.path().display().to_string()),
        "socket hors du dossier du test : {sock}"
    );
    e.click("ACTIONS");
    e.expect("New session");
}

/// Largeur de la sidebar (colonnes 0..44) : un clic en x = 40 tombe dans le blanc d'une ligne.
const BLANK_X: u16 = 40;

/// Un agent « check » (faux `claude`) dans la session `session`.
fn agent(e: &Env, session: &str) -> String {
    let pane = e.tmux(&["split-window", "-d", "-P", "-F", "#{pane_id}", "-t", session, "claude"]);
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs();
    let state = serde_json::json!({
        "pane": pane, "state": "check", "cwd": e.home(), "task": "Parse the notices",
        "question": "Which parser?", "options": ["pdfplumber", "PyMuPDF"],
        "updated_at": now, "model": "Opus", "ctx": 61
    });
    let file = e.dir.path().join("agents").join(format!("{}.json", &pane[1..]));
    std::fs::write(file, state.to_string()).unwrap();
    pane
}

#[test]
fn one_click_on_a_session_row_switches_to_it_even_in_the_blank_part() {
    let e = Env::start();
    e.tmux(&["new-session", "-d", "-s", "api"]);
    e.click("SESSIONS");
    let y = e.row_of(" api");
    e.click_at(BLANK_X, y);
    e.wait_tmux(&["list-clients", "-F", "#{client_session}"], "api");
}

#[test]
fn one_click_on_a_session_name_switches_to_it() {
    let e = Env::start();
    e.tmux(&["new-session", "-d", "-s", "api"]);
    e.click("SESSIONS");
    e.click(" api");
    e.wait_tmux(&["list-clients", "-F", "#{client_session}"], "api");
}

#[test]
fn one_click_on_an_agent_goes_to_its_pane() {
    let e = Env::start();
    e.tmux(&["new-session", "-d", "-s", "api"]);
    let pane = agent(&e, "api");
    e.click("AGENTS");
    let y = e.row_of("Parse the notices");
    e.click_at(BLANK_X, y);
    e.wait_tmux(&["list-clients", "-F", "#{client_session} #{pane_id}"], &format!("api {pane}"));
}

#[test]
fn one_click_on_a_folder_creates_the_session() {
    let e = Env::start();
    e.click("ACTIONS");
    e.click("New session");
    let y = e.row_of("~/dev/web");
    e.click_at(BLANK_X - 4, y); // dans le libellé « new » à droite
    e.wait_tmux(&["list-clients", "-F", "#{client_session}"], "web");
}

#[test]
fn a_typed_path_relative_to_home_creates_the_folder_and_the_session() {
    let e = Env::start();
    e.click("ACTIONS");
    e.click("New session");
    e.expect("NEW SESSION");
    e.type_text("lab/newproj");
    e.click("~/lab/newproj");
    e.wait_tmux(&["list-clients", "-F", "#{client_session}"], "newproj");
    assert!(e.home().join("lab/newproj").is_dir());
    assert_eq!(
        e.tmux(&["display", "-p", "-t", "=newproj:", "#{pane_current_path}"]),
        e.home().join("lab/newproj").display().to_string()
    );
}

#[test]
fn plus_new_project_creates_a_git_repo_next_to_the_other_projects_and_opens_it() {
    let e = Env::start();
    e.click("SESSIONS");
    e.click("+ New project");
    e.expect("NEW PROJECT");
    e.expect("in ~/lab"); // le dossier qui contient le plus de projets
    e.type_text("demo");
    e.expect("~/lab/demo");
    e.click("Create & open");
    e.wait_tmux(&["list-clients", "-F", "#{client_session}"], "demo");
    assert!(e.home().join("lab/demo/.git").is_dir());
}

#[test]
fn plus_row_of_the_new_session_screen_opens_new_project_with_the_typed_name() {
    let e = Env::start();
    e.click("ACTIONS");
    e.click("New session");
    e.expect("NEW SESSION"); // sinon le clic suivant vise encore l'onglet ACTIONS
    e.type_text("demo");
    e.click("+ New project");
    e.expect("~/lab/demo");
    e.click("Cancel");
    e.expect("ACTIONS");
    assert!(!e.home().join("lab/demo").exists());
}

#[test]
fn footer_keys_are_buttons_rename_by_mouse_only() {
    let e = Env::start();
    e.click("SESSIONS");
    e.click("rename");
    e.expect("RENAME SESSION main");
    e.type_text("\x7f\x7f\x7f\x7fhome");
    e.click("[ Rename ]");
    e.wait_tmux(&["list-sessions", "-F", "#{session_name}"], "home");
}

#[test]
fn header_filter_and_sort_are_buttons() {
    let e = Env::start();
    e.click("priority");
    e.expect("session ");
    e.click("/ filter agents");
    e.expect("esc clear");
}

#[test]
fn prefix_plus_opens_new_project_from_the_keyboard() {
    let e = Env::start();
    e.type_text("\x02+"); // Ctrl+B +
    e.expect("NEW PROJECT");
    e.type_text("kbd\r");
    e.wait_tmux(&["list-clients", "-F", "#{client_session}"], "kbd");
    assert!(e.home().join("lab/kbd/.git").is_dir());
}

#[test]
fn an_answer_button_sends_its_number_to_the_agent() {
    let e = Env::start();
    agent(&e, "main");
    e.click("PyMuPDF");
    let keys = e.dir.path().join("keys");
    let start = Instant::now();
    while std::fs::read_to_string(&keys).unwrap_or_default() != "2" {
        assert!(start.elapsed() < Duration::from_secs(5), "keys: {:?}", std::fs::read_to_string(&keys));
        std::thread::sleep(Duration::from_millis(100));
    }
}

#[test]
fn kill_a_session_by_mouse_only() {
    let e = Env::start();
    e.tmux(&["new-session", "-d", "-s", "api"]);
    e.click("SESSIONS");
    e.click(" api");
    e.wait_tmux(&["list-clients", "-F", "#{client_session}"], "api");
    e.click("kill");
    e.expect("KILL SESSION api");
    e.click("Save & kill");
    e.wait_tmux(&["list-sessions", "-F", "#{session_name}"], "main");
}

/// Ctrl+Shift+O / E tels que Ghostty les envoie (CSI u, config/ghostty/config) : un shell simple
/// à côté du pane de travail, jamais une deuxième sidebar ni un tmux imbriqué.
#[test]
fn ctrl_shift_o_and_e_split_the_work_pane_into_a_plain_shell() {
    let e = Env::start();
    let panes = || {
        let mut p: Vec<String> = e
            .tmux(&["list-panes", "-t", "main:", "-F", "#{@aif_sidebar}#{pane_current_command}"])
            .lines()
            .map(String::from)
            .collect();
        p.sort();
        p.join(" ")
    };
    // la sidebar (lancée par sh -c), le shell de départ, puis un shell par split
    for (seq, want) in [("\x1b[111;6u", "1sh sh sh"), ("\x1b[101;6u", "1sh sh sh sh")] {
        e.type_text(seq);
        let start = Instant::now();
        while panes() != want {
            assert!(start.elapsed() < Duration::from_secs(5), "{} != {want}", panes());
            std::thread::sleep(Duration::from_millis(100));
        }
    }
}

#[test]
fn help_box_and_footer_help_open_the_help_popup() {
    let e = Env::start();
    e.click("help");
    e.expect("NAVIGATE");
    e.type_text("\x1b"); // Esc ferme l'aide
    e.term.get_by_text("NAVIGATE").wait_hidden(Some(5000)).unwrap();
    e.click_at(42, e.row_of("ACTIONS")); // case « ? » de la barre d'onglets
    e.expect("NAVIGATE");
}

/// cargo build remplace le binaire (nouveau fichier, renommé) : la sidebar en cours se relance
/// sur le nouveau, sinon elle garde l'ancien code et `?` ne trouve plus son exécutable.
#[test]
fn a_rebuilt_binary_restarts_the_running_sidebar() {
    let e = Env::start();
    // exécutable du process sidebar (enfant du `sh -c` du pane) ; exec garde le même PID
    let exe = || {
        let panes = e.tmux(&["list-panes", "-a", "-F", "#{@aif_sidebar} #{pane_pid}"]);
        let sh = panes.lines().find(|l| l.starts_with("1 ")).unwrap()[2..].to_string();
        let out = Command::new("pgrep").args(["-P", &sh]).output().unwrap();
        let pid = String::from_utf8_lossy(&out.stdout).trim().to_string();
        std::fs::read_link(format!("/proc/{pid}/exe")).map(|p| p.display().to_string()).unwrap_or_default()
    };
    let bin = e.dir.path().join("aif-sidebar");
    std::fs::copy(&bin, e.dir.path().join("new")).unwrap();
    std::fs::rename(e.dir.path().join("new"), &bin).unwrap();
    let start = Instant::now();
    while exe().ends_with(" (deleted)") || exe().is_empty() {
        assert!(start.elapsed() < Duration::from_secs(5), "still on the old binary: {}", exe());
        std::thread::sleep(Duration::from_millis(100));
    }
    e.expect("SESSIONS 1");
    e.click("help");
    e.expect("NAVIGATE");
}
