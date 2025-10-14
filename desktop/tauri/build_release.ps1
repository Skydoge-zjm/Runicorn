[CmdletBinding()]
param(
  [string]$PythonExe = "python",
  # Bundles: nsis | msi
  [string]$Bundles = "nsis",
  # Skip frontend build if dist already exists
  [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"
try { if ($PSStyle) { $PSStyle.OutputRendering = 'PlainText' } } catch {}

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "OK: $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Warning $msg }
function Run($cmd, $cwd)  {
  Write-Verbose "[RUN] $cmd"
  if ($cwd) { Push-Location $cwd }
  try { & powershell -NoLogo -NoProfile -Command $cmd } finally { if ($cwd) { Pop-Location } }
}

# Resolve paths
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path         # .../desktop/tauri
$RepoRoot    = Resolve-Path (Join-Path $ScriptDir "../..")             # repo root
$SrcTauriDir = Resolve-Path (Join-Path $ScriptDir "src-tauri")         # .../desktop/tauri/src-tauri
$SidecarDir  = Resolve-Path (Join-Path $ScriptDir "sidecar")           # .../desktop/tauri/sidecar
$FrontendDir = Resolve-Path (Join-Path $RepoRoot "web/frontend")       # .../web/frontend

Write-Step "Repo: $RepoRoot"
Write-Step "src-tauri: $SrcTauriDir"
Write-Step "sidecar: $SidecarDir"
Write-Step "frontend: $FrontendDir"


Write-Step "Terminate leftover processes"
try { Run "Get-Process runicorn-viewer* -ErrorAction SilentlyContinue | Stop-Process -Force" $null } catch {}
try { Run "Get-Process runicorn-desktop* -ErrorAction SilentlyContinue | Stop-Process -Force" $null } catch {}
try { Run "taskkill /F /IM runicorn-viewer*.exe" $null } catch {}
try { Run "taskkill /F /IM runicorn-desktop*.exe" $null } catch {}


if (-not $SkipFrontend) {
  Write-Step "Frontend build (npm run build)"
  
  Run "npm run build" $FrontendDir
}
if ($SkipFrontend) {
  Write-Step "Skip frontend build (user requested)"
}
$FrontendDist = Join-Path $FrontendDir "dist"
if (-not (Test-Path $FrontendDist)) {
  throw "Frontend dist not found: $FrontendDist (build failed?)."
}
Write-Ok "Frontend dist: $FrontendDist"

# 1.5) Sync built frontend into Python package data (src/runicorn/webui)
Write-Step "Sync frontend dist -> src/runicorn/webui (for packaged sidecar)"
$PkgWebui = Join-Path $RepoRoot "src/runicorn/webui"
New-Item -ItemType Directory -Force $PkgWebui | Out-Null
try {
  Get-ChildItem -Force $PkgWebui | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
} catch {}
Copy-Item -Path (Join-Path $FrontendDist "*") -Destination $PkgWebui -Recurse -Force
Write-Ok "Webui synced: $PkgWebui"

Write-Step "Build sidecar (PyInstaller onefile)"
$SidecarScript = Join-Path $SidecarDir "build_sidecar.ps1"
if (-not (Test-Path $SidecarScript)) { throw "Sidecar script not found: $SidecarScript" }
Run "`"$SidecarScript`" -PythonExe `"$PythonExe`" -UseLocal" $RepoRoot

$HostTriple = (& rustc -Vv | Select-String "host:").Line.Split()[1]
$SidecarExe = Join-Path $SidecarDir "dist/runicorn-viewer-$HostTriple.exe"
if (-not (Test-Path $SidecarExe)) {
  throw "Sidecar not found: $SidecarExe"
}
Write-Ok "Sidecar: $SidecarExe"


Write-Step "Ensure icons/icon.ico"
$IconDir = Join-Path $SrcTauriDir "icons"
$IconIco = Join-Path $IconDir "icon.ico"
if (-not (Test-Path $IconIco)) {
  New-Item -ItemType Directory -Force $IconDir | Out-Null

  $IconSrc = Resolve-Path (Join-Path $RepoRoot "docs/assets/icon.jpg") -ErrorAction SilentlyContinue
  if (-not $IconSrc) { $IconSrc = Resolve-Path (Join-Path $RepoRoot "docs/assets/p1.png") -ErrorAction SilentlyContinue }
  if (-not $IconSrc) { throw "No source icon found at docs/assets/. Please add icon.jpg or p1.png." }
  try {
    Run "python -m pip install --user pillow" $null
    $py = @"
from PIL import Image
im = Image.open(r'''$($IconSrc)''')
im.save(r'''$($IconIco)''', sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
print('Wrote', r'''$($IconIco)''')
"@
    $tmp = New-TemporaryFile
    Set-Content -Path $tmp -Value $py -Encoding UTF8
    Run "python `"$tmp`"" $null
    Remove-Item $tmp -Force
  } catch {
    throw "Failed to create icons/icon.ico automatically. Please create it manually."
  }
}
Write-Ok "Icon: $IconIco"


$env:RUNICORN_FRONTEND_DIST = (Resolve-Path $FrontendDist)

Write-Step "Cargo tauri build ($Bundles)"
if ($Bundles -notin @('nsis','msi')) { throw "Invalid Bundles: $Bundles (use nsis or msi)" }
Run "cargo tauri build --bundles $Bundles" $SrcTauriDir

$BundleDir = Join-Path $SrcTauriDir "target/release/bundle"
if ($Bundles -eq 'nsis') {
  $Installer = Get-ChildItem -Path (Join-Path $BundleDir 'nsis') -Filter '*_x64-setup.exe' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($Installer) { Write-Ok "Installer: $($Installer.FullName)" } else { Write-Warn "NSIS installer not found under $BundleDir\nsis" }
} elseif ($Bundles -eq 'msi') {
  $Msi = Get-ChildItem -Path (Join-Path $BundleDir 'msi') -Filter '*.msi' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($Msi) { Write-Ok "Installer: $($Msi.FullName)" } else { Write-Warn "MSI not found under $BundleDir\msi" }
}

Write-Host "Done." -ForegroundColor Green
