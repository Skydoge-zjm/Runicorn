[English](README.md) | [简体中文](README_zh.md)

# Runicorn Desktop (Tauri)

This directory contains the desktop wrapper for the Runicorn viewer. It is a developer-facing build and maintenance note for the Windows Tauri packaging path, not end-user usage documentation.

The desktop app consists of two build surfaces:

- the frontend bundle from `web/frontend`
- the packaged Python sidecar built under `desktop/tauri/sidecar`

The Rust/Tauri app loads the built frontend assets and launches the packaged sidecar executable.

## Prerequisites (Windows)

Install once:

1. Rust toolchain (`rustup`)

```powershell
winget install --id Rustlang.Rustup -e
```

2. MSVC build tools with Windows SDK

```powershell
winget install --id Microsoft.VisualStudio.2022.BuildTools -e
```

Select `Desktop development with C++` in the installer.

3. WebView2 Runtime

```powershell
winget install --id Microsoft.EdgeWebView2Runtime -e
```

4. Node.js LTS

```powershell
winget install OpenJS.NodeJS.LTS -e
```

5. Tauri CLI

```powershell
cargo install tauri-cli
```

6. A Python interpreter suitable for the sidecar build

The current local build scripts are designed to read this from configuration. On this repository, Python build/test commands are expected to use the `runicorn_dev` Conda environment.

## Build Configuration

Desktop build parameters are configuration-driven.

- shared defaults: `desktop/tauri/build_config.json`
- personal machine override: `desktop/tauri/build_config.local.json`
- sample local override: `desktop/tauri/build_config.local.example.json`

`build_config.local.json` is intentionally git-ignored. Use it for machine-specific values such as:

- `common.pythonExe`
- `common.httpProxy`
- `common.httpsProxy`
- `common.noProxy`

Important behavior:

- local overrides replace shared defaults recursively
- desktop build scripts print the merged effective config at startup
- all desktop build scripts support `-DryRun`
- non-local sidecar builds do not have a default package version; if `sidecar.useLocal` is `false`, pass `-RunicornVersion` explicitly

Key configuration sections:

- `common`
  - shared process-level settings such as Python path and proxy values
- `sidecar`
  - sidecar build mode and runtime probe settings
- `sidecar.pyInstaller`
  - PyInstaller collection and DLL inclusion settings
- `release`
  - desktop bundle defaults such as `bundles` and `skipFrontend`

## Script Roles

### `build_release_clean.ps1`

Primary desktop build entry point.

Use this when frontend or sidecar-related code may have changed and you want a full rebuild from a clean-enough state.

It will:

- stop leftover desktop/sidecar processes
- rebuild the frontend bundle
- rebuild the sidecar executable
- run `cargo tauri build`

Typical usage:

```powershell
./desktop/tauri/build_release_clean.ps1
```

Dry-run:

```powershell
./desktop/tauri/build_release_clean.ps1 -DryRun
```

### `build_release.ps1`

Regular desktop release build entry point.

This is similar to `build_release_clean.ps1`, but is better suited when you already know the frontend build state and want a less aggressive path. If you are unsure, use `build_release_clean.ps1`.

### `sidecar/build_sidecar.ps1`

Sidecar-only build entry point.

It will:

- prepare or refresh the sidecar virtual environment
- install sidecar dependencies
- build `runicorn-viewer.exe` with PyInstaller
- inject required runtime DLLs for the selected Python base environment
- create the target-triple suffixed executable required by Tauri
- run a runtime health probe against `/api/health`

Use this when you only changed Python viewer/backend packaging behavior or when debugging sidecar failures.

Typical usage:

```powershell
./desktop/tauri/sidecar/build_sidecar.ps1
```

Non-local package build:

```powershell
./desktop/tauri/sidecar/build_sidecar.ps1 -RunicornVersion 0.7.2
```

### `build_config.ps1`

Helper layer shared by the build scripts.

It is not a standalone entry point. It loads and merges configuration, applies proxy-related environment variables in process scope, and provides the config-printing / dry-run helpers used by the other scripts.

## Recommended Workflows

### Frontend and desktop both changed

Use:

```powershell
./desktop/tauri/build_release_clean.ps1
```

### Only the sidecar path changed

Use:

```powershell
./desktop/tauri/sidecar/build_sidecar.ps1
```

### Only inspect resolved parameters

Use:

```powershell
./desktop/tauri/build_release_clean.ps1 -DryRun
```

## Current Build Output

The local Windows packaging flow currently targets NSIS by default through the desktop build configuration.

The expected successful release output is:

- `desktop/tauri/src-tauri/target/release/runicorn-desktop.exe`
- `desktop/tauri/src-tauri/target/release/bundle/nsis/Runicorn Desktop_<version>_x64-setup.exe`

The sidecar output is expected at:

- `desktop/tauri/sidecar/dist/runicorn-viewer.exe`
- `desktop/tauri/sidecar/dist/runicorn-viewer-<target-triple>.exe`

## CI Validation Boundary

The repository treats desktop validation as a separate automation surface from the main CI.

- main CI continues to run Python/frontend checks plus frontend mocked browser smoke
- the current Python CI path still relies on the default `pytest -q` run, which includes the current integration-marked suite
- desktop validation lives in `.github/workflows/desktop-build.yml`

The desktop workflow currently performs a narrower validation pass than a full installer build:

- build frontend assets
- run `desktop/tauri/sidecar/build_sidecar.ps1`
- run `cargo check` in `desktop/tauri/src-tauri`

Important limitation:

- CI currently validates the sidecar packaging/runtime probe and Rust compile surface
- CI does not currently build the full Windows installer on every run

## Development Notes

- The desktop scripts are the supported packaging entry points; do not treat raw `cargo tauri build` as the canonical top-level workflow when sidecar/frontend rebuilds are required.
- The checked-in `runicorn-viewer.spec` is intentionally generic. The sidecar build script generates a temporary spec during packaging so machine-specific DLL paths are not persisted in the repository.
- If a local machine needs proxies or a non-default Python interpreter, put that in `build_config.local.json` instead of editing tracked scripts.
