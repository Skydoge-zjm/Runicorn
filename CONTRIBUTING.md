# Contributing to Runicorn

Thanks for your interest in contributing! This project aims to provide a lightweight, 100% local experiment tracking and visualization experience.

## Ground rules
- Be respectful. Keep discussions constructive.
- Prefer issues before large PRs. Share context and alternatives.
- Small, focused PRs are easier to review and merge.

## Development setup
Prerequisites:
- Python 3.8+
- Node.js 18+ and npm (for frontend)

Steps (Windows PowerShell examples):
```powershell
# 1) Create and activate venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Backend deps (for dev server)
pip install -r web/backend/requirements.txt

# 3) Frontend deps
cd web/frontend
npm install
cd ../..

# 4) One-click dev (backend + frontend with proxy)
./run_dev.ps1 -PythonExe "python"
# Open http://127.0.0.1:5173 (proxies /api/* to 127.0.0.1:8000)
```

Optional static checks:
```powershell
pip install ruff mypy
# Lint
ruff check .
# (Optional) Format
ruff format .
# Type check (best effort)
mypy src
```

## Project layout
- Python package under `src/runicorn/` with a read-only FastAPI viewer (`viewer.py`) and CLI (`cli.py`).
- Web UI under `web/frontend/` (React + Vite + Ant Design + ECharts). Built files are bundled into wheels under `src/runicorn/webui/`.
- Example script: `examples/create_test_run.py` (generates a synthetic run in `./.runicorn/`).

## Commit style and branching
- Use Conventional Commits where possible:
  - `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `perf:`, `test:`, `build:`, `ci:`
- Branch naming: `feature/<name>`, `fix/<name>`, `docs/<name>`.
- Keep PRs small. Include:
  - What/Why summary
  - Screenshots for UI changes (before/after)
  - Testing notes

## Tests
There is no formal test suite yet. For now, validate by:
- Running `examples/create_test_run.py`
- Launching the viewer via `runicorn viewer` or `./run_dev.ps1`
- Checking metrics tables, charts, logs websocket, and GPU panel (if `nvidia-smi` is available)

## Releasing (maintainers)
- Bump version via the release script (also builds frontend):
```powershell
./publish.ps1 -Repository pypi -NewVersion "X.Y.Z"
```
- Create a tag `vX.Y.Z` and update `CHANGELOG.md` accordingly.

## Code of Conduct
Please be respectful. If a Code of Conduct file is added later, it will apply to all interactions.
