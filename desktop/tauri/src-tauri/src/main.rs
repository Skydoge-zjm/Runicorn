#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    net::{SocketAddr, TcpStream},
    process::{Child, Command, Stdio},
    thread,
    time::Duration,
    sync::Mutex,
    path::PathBuf,
};

use tauri::{AppHandle, Manager, WindowEvent, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_shell::{ShellExt};
use tauri_plugin_shell::process::CommandChild as ShellChild;

fn is_port_available(port: u16) -> bool {
    let addr = SocketAddr::from(([127, 0, 0, 1], port));
    TcpStream::connect(addr).is_err()
}

fn repo_frontend_dist_guess() -> Option<PathBuf> {
    // Try ../../../web/frontend/dist relative to current dir (dev layout)
    if let Ok(mut p) = std::env::current_dir() {
        let mut try1 = p.clone();
        try1.push("../../../web/frontend/dist");
        if try1.exists() {
            return Some(try1);
        }
        // Try project root /web/frontend/dist
        p.push("web/frontend/dist");
        if p.exists() {
            return Some(p);
        }
    }
    None
}

fn pick_port() -> u16 {
    let preferred = 8000u16;
    if is_port_available(preferred) {
        return preferred;
    }
    // try a few ephemeral ports
    for p in 49152..=65535 {
        if is_port_available(p) {
            return p;
        }
    }
    preferred
}

fn repo_src_dir_guess() -> Option<PathBuf> {
    // Best-effort: try ../../../src relative to this src-tauri binary location during dev
    if let Ok(mut p) = std::env::current_dir() {
        // common case: running from desktop/tauri
        let mut try1 = p.clone();
        try1.push("../../../src");
        if try1.exists() {
            return Some(try1);
        }
        // try project root /src
        p.push("src");
        if p.exists() {
            return Some(p);
        }
    }
    None
}

fn spawn_backend(port: u16, app: &AppHandle) -> Option<BackendChild> {
    // 1) Try sidecar first (no Python required for end users)
    if let Some(dist) = repo_frontend_dist_guess() {
        // Make the viewer serve our built frontend at '/'
        std::env::set_var("RUNICORN_FRONTEND_DIST", dist.to_string_lossy().as_ref());
    }
    if let Ok(cmd) = app.shell().sidecar("runicorn-viewer") {
        if let Ok((_rx, child)) = cmd.args(["--port", &port.to_string()]).spawn() {
            return Some(BackendChild::Sidecar(child));
        }
    }

    // 2) Fallback: spawn python-based backend (dev-friendly)
    let python = std::env::var("RUNICORN_DESKTOP_PY").unwrap_or_else(|_| "python".to_string());
    let mut cmd = Command::new(python);
    cmd.args([
        "-X", "utf8",
        "-m", "uvicorn",
        "runicorn.viewer:create_app",
        "--factory",
        "--host", "127.0.0.1",
        "--port", &port.to_string(),
    ])
    .stdin(Stdio::null())
    .stdout(Stdio::null())
    .stderr(Stdio::null());
    if let Some(src_dir) = repo_src_dir_guess() {
        let py_path_key = "PYTHONPATH";
        let mut val = std::env::var(py_path_key).unwrap_or_default();
        if !val.is_empty() { if cfg!(target_os = "windows") { val.push(';') } else { val.push(':') } }
        val.push_str(&src_dir.to_string_lossy());
        cmd.env(py_path_key, val);
    }
    if let Some(dist) = repo_frontend_dist_guess() {
        cmd.env("RUNICORN_FRONTEND_DIST", dist.to_string_lossy().as_ref());
    }
    cmd.spawn().ok().map(BackendChild::Python)
}

fn wait_ready(port: u16, timeout_secs: u64) -> bool {
    let url = format!("http://127.0.0.1:{}/api/health", port);
    let mut waited = 0u64;
    while waited < timeout_secs {
        let resp = ureq::get(&url).timeout(Duration::from_secs(1)).call();
        if resp.is_ok() {
            return true;
        }
        thread::sleep(Duration::from_millis(300));
        waited += 0; // no-op
        // track in seconds roughly
        if waited % 3 == 0 { /* tick */ }
        waited += 1;
    }
    false
}

#[tauri::command]
fn get_backend_url(state: tauri::State<'_, AppState>) -> String {
    state
        .backend_url
        .lock()
        .unwrap()
        .clone()
        .unwrap_or_else(|| "http://127.0.0.1:8000".into())
}

enum BackendChild {
    Sidecar(ShellChild),
    Python(Child),
}

struct AppState {
    child: Mutex<Option<BackendChild>>,
    backend_url: Mutex<Option<String>>,
}

fn kill_child(state: &tauri::State<'_, AppState>) {
    if let Some(child) = state.child.lock().unwrap().take() {
        match child {
            BackendChild::Sidecar(c) => {
                let _ = c.kill();
            }
            BackendChild::Python(mut c) => {
                let _ = c.kill();
                let _ = c.wait();
            }
        }
    }
}

fn start(app: AppHandle) {
    let port = pick_port();
    let child = spawn_backend(port, &app).expect("failed to spawn backend (sidecar/python)");

    let state: tauri::State<AppState> = app.state();
    *state.child.lock().unwrap() = Some(child);

    if !wait_ready(port, 20) {
        // still show window, but将来可弹错误提示
    }
    let url = format!("http://127.0.0.1:{}/", port);
    *state.backend_url.lock().unwrap() = Some(url.clone());

    WebviewWindowBuilder::new(&app, "main", WebviewUrl::External(url.parse().unwrap()))
        .title("Runicorn")
        .resizable(true)
        .build()
        .expect("failed to create window");
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(AppState { child: Mutex::new(None), backend_url: Mutex::new(None) })
        .setup(|app| {
            // spawn backend in a background thread to avoid blocking
            let handle = app.handle().clone();
            thread::spawn(move || start(handle));
            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { .. } = event {
                let app = window.app_handle();
                let state: tauri::State<AppState> = app.state();
                kill_child(&state);
            }
        })
        .invoke_handler(tauri::generate_handler![get_backend_url])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
