[CmdletBinding()]
param(
  [string]$PythonExe = "python",
  [ValidateSet("nsis","msi")]
  [string]$Bundles = "nsis",
  [switch]$SkipFrontend,
  [switch]$Verbose
)

$ErrorActionPreference = "Stop"
try { if ($PSStyle) { $PSStyle.OutputRendering = 'PlainText' } } catch {}

function Step($m) { Write-Host "==> $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "OK: $m" -ForegroundColor Green }
function Warn($m) { Write-Warning $m }
function RunCmd([string]$cmd, [string]$cwd) {
  if ($Verbose) { Write-Host "[RUN] $cmd" -ForegroundColor DarkGray }
  if ($cwd) { Push-Location $cwd }
  try { & powershell -NoLogo -NoProfile -Command $cmd } finally { if ($cwd) { Pop-Location } }
}

# Paths
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot    = Resolve-Path (Join-Path $ScriptDir "../..")
$SrcTauriDir = Resolve-Path (Join-Path $ScriptDir "src-tauri")
$SidecarDir  = Resolve-Path (Join-Path $ScriptDir "sidecar")
$FrontendDir = Resolve-Path (Join-Path $RepoRoot "web/frontend")

Step "Repo: $RepoRoot"
Step "src-tauri: $SrcTauriDir"
Step "sidecar: $SidecarDir"
Step "frontend: $FrontendDir"

# Kill leftover processes
Step "Terminate leftover processes"
try { taskkill /F /IM runicorn-viewer*.exe 2>$null | Out-Null } catch {}
try { taskkill /F /IM runicorn-desktop*.exe 2>$null | Out-Null } catch {}

# Frontend build
if (-not $SkipFrontend.IsPresent) {
  Step "Frontend build (npm run build)"
  RunCmd "npm run build" $FrontendDir
} else {
  Step "Skip frontend build (user requested)"
}
$FrontendDist = Join-Path $FrontendDir "dist"
if (-not (Test-Path $FrontendDist)) { throw "Frontend dist not found: $FrontendDist" }
Ok "Frontend dist: $FrontendDist"

# Sidecar build
Step "Build sidecar (PyInstaller onefile)"
$SidecarScript = Join-Path $SidecarDir "build_sidecar.ps1"
if (-not (Test-Path $SidecarScript)) { throw "Sidecar script not found: $SidecarScript" }
Push-Location $RepoRoot
& $SidecarScript -PythonExe $PythonExe -UseLocal
Pop-Location

# Validate sidecar output
$HostTriple = (& rustc -Vv | Select-String "host:").Line.Split()[1]
$SidecarExe = Join-Path $SidecarDir ("dist/runicorn-viewer-" + $HostTriple + ".exe")
if (-not (Test-Path $SidecarExe)) { throw "Sidecar not found: $SidecarExe" }
Ok "Sidecar: $SidecarExe"

# Ensure icons/icon.ico
Step "Ensure icons/icon.ico"
$IconDir = Join-Path $SrcTauriDir "icons"
$IconIco = Join-Path $IconDir "icon.ico"
if (-not (Test-Path $IconIco)) {
  New-Item -ItemType Directory -Force $IconDir | Out-Null
  $IconSrc = Resolve-Path (Join-Path $RepoRoot "docs/assets/icon.jpg") -ErrorAction SilentlyContinue
  if (-not $IconSrc) { $IconSrc = Resolve-Path (Join-Path $RepoRoot "docs/assets/p1.png") -ErrorAction SilentlyContinue }
  if (-not $IconSrc) { throw "No source icon found at docs/assets/. Please add icon.jpg or p1.png." }
  $py = @"
from PIL import Image
im = Image.open(r'''$($IconSrc)''')
im.save(r'''$($IconIco)''', sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
print('Wrote', r'''$($IconIco)''')
"@
  $tmp = New-TemporaryFile
  Set-Content -Path $tmp -Value $py -Encoding UTF8
  try {
    RunCmd "python -m pip install --user pillow" $null
    RunCmd "python `"$tmp`"" $null
  } finally { Remove-Item $tmp -Force }
}
Ok "Icon: $IconIco"

# Export frontend dist for fallback
$env:RUNICORN_FRONTEND_DIST = (Resolve-Path $FrontendDist)

# Build installer
Step "Cargo tauri build ($Bundles)"
RunCmd "cargo tauri build --bundles $Bundles" $SrcTauriDir

# Print output path
$BundleDir = Join-Path $SrcTauriDir "target/release/bundle"
if ($Bundles -eq 'nsis') {
  $Installer = Get-ChildItem -Path (Join-Path $BundleDir 'nsis') -Filter '*_x64-setup.exe' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($Installer) { Ok ("Installer: " + $Installer.FullName) } else { Warn ("NSIS installer not found under " + (Join-Path $BundleDir 'nsis')) }
} else {
  $Msi = Get-ChildItem -Path (Join-Path $BundleDir 'msi') -Filter '*.msi' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($Msi) { Ok ("Installer: " + $Msi.FullName) } else { Warn ("MSI not found under " + (Join-Path $BundleDir 'msi')) }
}

Write-Host "Done." -ForegroundColor Green
