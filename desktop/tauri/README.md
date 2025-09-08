# Runicorn Desktop (Tauri)

This is a lightweight desktop wrapper around the Runicorn viewer using Tauri (system WebView). It spawns the backend (uvicorn + FastAPI) and opens a native window to the UI.

## Prerequisites (Windows)

Install once, reuse forever:

1) Rust toolchain (rustup)

```powershell
winget install --id Rustlang.Rustup -e
```

2) MSVC build tools (C++ workload)

```powershell
winget install --id Microsoft.VisualStudio.2022.BuildTools -e
# In the installer, select "Desktop development with C++" (MSVC & Windows 10/11 SDK)
```

3) WebView2 Runtime (if not already installed)

```powershell
winget install --id Microsoft.EdgeWebView2Runtime -e
```

4) Node.js LTS (for building the frontend)

```powershell
winget install OpenJS.NodeJS.LTS -e
```

5) Tauri CLI (choose one)

```powershell
# via cargo
cargo install tauri-cli
# or via npm	npm i -g @tauri-apps/cli
```

## Develop

From the repo root:

```powershell
# Build frontend once (Tauri is configured to load the built dist)
cd web/frontend
npm install
npm run build

# Run the desktop app (spawns backend automatically)
cd ../../desktop/tauri/src-tauri
cargo tauri dev
```

Notes:
- The app will auto-pick a free port (prefers 8000) and open the UI.
- If Python is not on PATH or you prefer a specific interpreter, set env:

```powershell
# Example: point to your Anaconda/venv Python
$env:RUNICORN_DESKTOP_PY = "E:\\Anaconda\\envs\\pytorch\\python.exe"
```

The launcher tries to locate the repo's `src/` and appends it to `PYTHONPATH` automatically in dev, so the `runicorn` module resolves even without installation.

## Build (Release)

```powershell
# Ensure frontend is built
npm --prefix ../../../web/frontend run build

# Build desktop bundle (.msi/.exe depending on config)
cd ../../desktop/tauri/src-tauri
cargo tauri build
```

The current build starts the backend by invoking `python -m uvicorn runicorn.viewer:create_app --factory`. For end-user distribution without Python, package the backend as a sidecar (see below).

## Roadmap: Sidecar Backend (no Python requirement)

- Use PyInstaller to create a `runicorn-viewer.exe` from a small launcher that imports `runicorn.viewer:create_app`.
- Add it as a Tauri sidecar in `tauri.conf.json` and spawn it from Rust instead of `python`.
- This removes the Python dependency for end users, while keeping the same local/readonly design.

