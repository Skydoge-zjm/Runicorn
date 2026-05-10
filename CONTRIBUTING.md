# Contributing to Runicorn

Thanks for your interest in contributing! This project aims to provide a lightweight, 100% local experiment tracking and visualization experience.

## Ground rules
- Be respectful. Keep discussions constructive.
- Prefer issues before large PRs. Share context and alternatives.
- Small, focused PRs are easier to review and merge.

## Development setup
Prerequisites:
- Python 3.10+
- Node.js 18+ and npm (for frontend)

Steps (Windows PowerShell examples):
```powershell
# 1) Create and activate venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Install Runicorn in editable mode
pip install -e .

# 3) Dev tools used in this repo
pip install pytest ruff mypy

# 4) Frontend deps
cd web/frontend
npm ci
cd ../..

# 5) Optional: one-click dev (backend + frontend with proxy)
./run_dev.ps1 -PythonExe "python"
# Open http://127.0.0.1:5173 (proxies /api/* to 127.0.0.1:8000)
```

If you prefer to run services manually:
```powershell
# Backend
python -m uvicorn runicorn.viewer:create_app --factory --host 127.0.0.1 --port 8000 --reload

# Frontend (new terminal)
cd web/frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Optional static checks:
```powershell
# Lint
ruff check .
# (Optional) Format
ruff format .
# Type check (best effort)
mypy src
```

## Project layout
- Python package under `src/runicorn/` with a FastAPI viewer in `src/runicorn/viewer/` and CLI entrypoint in `src/runicorn/cli.py`.
- **Remote Viewer** (v0.5.0): SSH-based remote access under `src/runicorn/remote/` with connection management, environment detection, and viewer lifecycle.
- Web UI under `web/frontend/` (React + Vite + Ant Design + ECharts). Built files are bundled into wheels under `src/runicorn/webui/`.
- Remote UI components: `web/frontend/src/pages/RemoteViewerPage.tsx`, `web/frontend/src/components/remote/`, and the shared frontend API client in `web/frontend/src/api.ts`.
- Example script: `examples/create_test_run.py` (generates a synthetic run in `./.runicorn/`).

## Commit style and branching
- Use Conventional Commits where possible:
  - `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `perf:`, `test:`, `build:`, `ci:`
- Branch naming: `feature/<name>`, `fix/<name>`, `docs/<name>`.
- Keep PRs small. Include:
  - What/Why summary
  - Screenshots for UI changes (before/after)
  - Testing notes

## Developing Remote Viewer (v0.5.0)

### Setup for Remote Development

Remote Viewer requires a test environment with SSH access:

1. **Local development machine**:
   ```bash
   # Install with dev dependencies
   pip install -e ".[dev]"
   ```

2. **Remote test server** (Linux/WSL):
   - Install Runicorn on the remote server: `pip install runicorn`
   - Configure SSH key-based authentication
   - Ensure remote Python 3.10+ is accessible

### Testing Remote Features

```bash
# Local SSH backend coverage
pytest tests/unit/remote/test_ssh_backend.py -q

# Integration suite
pytest tests/integration -q

# Manual remote smoke test
runicorn viewer
# Navigate to Remote page in browser
# Connect to test server and start Remote Viewer
```

### Remote Viewer Code Structure

```
src/runicorn/remote/
├── __init__.py              # Module exports
├── connection.py            # SSH connection management
├── environment.py           # Environment detection
├── viewer/
│   ├── __init__.py
│   ├── manager.py           # Viewer lifecycle management
│   ├── launcher.py          # Launch logic
│   └── tunnel.py            # SSH tunnel handling
└── config.py                # Configuration

web/frontend/src/
├── pages/
│   └── RemoteViewerPage.tsx # Remote main page
├── components/remote/       # Remote-specific components
│   ├── CondaEnvSelector.tsx
│   ├── HostKeyModal.tsx
│   ├── RemoteConfigCard.tsx
│   └── RemoteSessionCard.tsx
└── api.ts                   # Shared frontend API client
```

### Guidelines for Remote Features

- **SSH security**: Always validate host keys, never store passwords in plain text
- **Error handling**: Provide clear error messages for SSH failures
- **Cleanup**: Ensure remote resources (temp files, processes) are cleaned up on disconnect
- **Documentation**: Update API docs (`docs/api/zh/remote_api.md`) and user guide (`docs/guides/zh/REMOTE_VIEWER_GUIDE.md`)
- **Testing**: Test on actual remote servers, not just localhost SSH

### Common Remote Issues

- **Connection timeout**: Check SSH config, firewall rules, and network stability
- **Permission denied**: Verify SSH key permissions (chmod 600)
- **Remote Viewer won't start**: Ensure Runicorn is installed on remote server
- **Port conflicts**: Check if local ports 8081-8199 are available

---

## Tests
For routine changes, run the suites that match your surface area:
- `pytest tests/unit -q`
- `pytest tests/integration -q`
- `cd web/frontend && npm test`
- `cd web/frontend && npm run build`
- `ruff check .`

When touching SSH flows or full-stack behavior, add a manual smoke test with `runicorn viewer` (or `./run_dev.ps1`) and verify the affected UI/API path end to end.

## Releasing (maintainers)
- Bump version via the release script (also builds frontend):
```powershell
./publish.ps1 -Repository pypi -NewVersion "X.Y.Z"
```
- Create a tag `vX.Y.Z` and update `CHANGELOG.md` accordingly.

## Code of Conduct
Please be respectful. If a Code of Conduct file is added later, it will apply to all interactions.
