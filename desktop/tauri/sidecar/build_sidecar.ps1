[CmdletBinding()]
param(
  [string]$PythonExe = "python",
  [string]$RunicornVersion = "0.2.0",
  [switch]$UseLocal
)

$ErrorActionPreference = "Stop"
# PowerShell 5.1 doesn't have $PSStyle; guard usage for compatibility
try { if ($PSStyle) { $PSStyle.OutputRendering = 'PlainText' } } catch {}

Write-Host "==> Building Runicorn sidecar (PyInstaller)" -ForegroundColor Cyan

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $here

try {
  # 1) Create venv
  if (-not (Test-Path ".venv")) {
    & $PythonExe -m venv .venv
  }
  $venvPy = Join-Path $here ".venv/Scripts/python.exe"
  if (-not (Test-Path $venvPy)) { throw "venv python not found: $venvPy" }

  # 2) Install deps using venv python
  & $venvPy -m pip install -U pip wheel setuptools
  & $venvPy -m pip install -U pyinstaller
  if ($UseLocal) {
    $repoRoot = Resolve-Path "$here/../../../"
    Write-Host "Installing runicorn from local repo: $repoRoot" -ForegroundColor Yellow
    & $venvPy -m pip install -U "$repoRoot"
  } else {
    Write-Host "Installing runicorn==$RunicornVersion from PyPI" -ForegroundColor Yellow
    & $venvPy -m pip install -U "runicorn==$RunicornVersion"
  }

  # 3) Build onefile executable
  if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
  if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
  & $venvPy -m PyInstaller --noconfirm --noconsole --onefile --collect-all runicorn --name runicorn-viewer (Join-Path $here "run_viewer_app.py")

  $oneFile = Join-Path $here "dist/runicorn-viewer.exe"
  $oneDir  = Join-Path $here "dist/runicorn-viewer/runicorn-viewer.exe"
  if (Test-Path $oneFile) {
    Write-Host "OK: $oneFile" -ForegroundColor Green
  } elseif (Test-Path $oneDir) {
    # Fallback in case PyInstaller ignored --onefile; copy to expected path
    New-Item -ItemType Directory -Force (Split-Path $oneFile) | Out-Null
    Copy-Item $oneDir $oneFile -Force
    Write-Host "OK: $oneFile (copied from onedir output)" -ForegroundColor Yellow
  } else {
    throw "PyInstaller did not produce $oneFile or $oneDir"
  }

  # 4) Produce Tauri v2 expected filename with target triple suffix
  #    externalBin entry is '../sidecar/dist/runicorn-viewer' (no extension),
  #    so Tauri looks for 'runicorn-viewer-<target_triple>.exe'.
  try {
    $rustInfo = & rustc -Vv 2>$null
    $triple = ($rustInfo | Select-String "host:").Line.Split()[1]
  } catch {
    $triple = $null
  }
  if ($null -ne $triple -and $triple.Trim() -ne "") {
    $suffixed = Join-Path $here ("dist/runicorn-viewer-" + $triple + ".exe")
    Copy-Item $oneFile $suffixed -Force
    Write-Host "OK: $suffixed (required by Tauri v2 externalBin)" -ForegroundColor Green
    # Compatibility: some setups may search for 'runicorn-viewer.exe-<triple>.exe'
    $compat = Join-Path $here ("dist/runicorn-viewer.exe-" + $triple + ".exe")
    Copy-Item $oneFile $compat -Force
    Write-Host "OK: $compat (compatibility name)" -ForegroundColor Yellow
  } else {
    Write-Warning "Could not determine Rust target triple; if cargo tauri build/dev complains, run 'rustc -Vv' and copy runicorn-viewer.exe to runicorn-viewer-<triple>.exe manually."
  }
}
finally {
  Pop-Location
}
