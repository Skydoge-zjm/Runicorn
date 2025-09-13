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
  # 1) Create/refresh venv (recreate if base interpreter differs)
  function Get-BasePrefix([string]$py) { & $py -c "import sys; print(sys.base_prefix)" 2>$null }
  $venvDir = Join-Path $here ".venv"
  $venvPy = Join-Path $venvDir "Scripts/python.exe"
  $needRecreate = $false
  if (Test-Path $venvDir) {
    if (Test-Path $venvPy) {
      $curBase = Get-BasePrefix $venvPy
      $reqBase = Get-BasePrefix $PythonExe
      if ($curBase -ne $reqBase) {
        Write-Host "Recreating venv due to base interpreter change:`n  current: $curBase`n  requested: $reqBase" -ForegroundColor Yellow
        $needRecreate = $true
      }
    } else { $needRecreate = $true }
  } else { $needRecreate = $true }
  if ($needRecreate) {
    if (Test-Path $venvDir) { Remove-Item -Recurse -Force $venvDir }
    & $PythonExe -m venv --clear $venvDir
  }
  if (-not (Test-Path $venvPy)) { throw "venv python not found: $venvPy" }

  # 2) Install deps using venv python
  & $venvPy -m pip install -U pip wheel setuptools
  & $venvPy -m pip install -U pyinstaller
  if ($UseLocal) {
    $repoRoot = Resolve-Path "$here/../../../"
    Write-Host "Installing runicorn from local repo: $repoRoot" -ForegroundColor Yellow
    & $venvPy -m pip install -U --force-reinstall --no-cache-dir "$repoRoot"
  } else {
    Write-Host "Installing runicorn==$RunicornVersion from PyPI" -ForegroundColor Yellow
    & $venvPy -m pip install -U "runicorn==$RunicornVersion"
  }
  # Ensure form parser dependency required by Starlette/FastAPI
  & $venvPy -m pip install -U python-multipart

  # 3) Build onefile executable
  if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
  if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

  # Attempt to include essential base DLLs from the interpreter that created the venv
  # Some environments (e.g., Anaconda present on PATH) may confuse PyInstaller analysis
  # and miss libmpdec/libexpat. We proactively add them from sys.base_prefix/DLLs if present.
  $baseRoot = (& $venvPy -c "import sys,os; print(sys.base_prefix)" 2>$null).Trim()
  $baseDlls = (& $venvPy -c "import sys,os; print(os.path.join(sys.base_prefix, 'DLLs'))" 2>$null).Trim()
  $addBinArgs = @()
  function Add-DllsFrom([string]$dir, [string[]]$patterns) {
    if (-not $dir -or -not (Test-Path $dir)) { return }
    foreach ($pat in $patterns) {
      $items = Get-ChildItem -Path $dir -Filter $pat -ErrorAction SilentlyContinue
      foreach ($f in $items) {
        $global:addBinArgs += @("--add-binary", ("{0};." -f $f.FullName))
      }
    }
  }

  $patterns = @("libmpdec*.dll","mpdecimal*.dll","libexpat*.dll","libssl*.dll","libcrypto*.dll","liblzma*.dll","libbz2*.dll","zlib*.dll","vcruntime*.dll")
  Add-DllsFrom $baseDlls $patterns
  Add-DllsFrom $baseRoot $patterns
  if ($addBinArgs.Count -gt 0) {
    Write-Host ("Including base DLLs from: {0}; {1}" -f $baseDlls, $baseRoot) -ForegroundColor Yellow
    $addBinArgs | ForEach-Object { Write-Host ("  " + $_) -ForegroundColor DarkYellow }
  }

  # Sanitize PATH to avoid PyInstaller picking Anaconda DLLs during analysis
  $oldPath = $env:PATH
  try {
    # Unset common Conda env vars to avoid PyInstaller picking conda paths
    $conEnv = @('CONDA_PREFIX','CONDA_DEFAULT_ENV','CONDA_EXE','CONDA_SHLVL','CONDA_PROMPT_MODIFIER','PYTHONHOME')
    $backup = @{}
    foreach ($k in $conEnv) { if (Test-Path Env:$k) { $backup[$k] = (Get-Item Env:$k).Value; Remove-Item Env:$k } }
    $env:PATH = ($oldPath -split ';' | Where-Object { $_ -notmatch '(?i)conda' -and $_ -notmatch '(?i)anaconda' -and $_ -notmatch '(?i)miniconda' }) -join ';'
    & $venvPy -m PyInstaller `
      --noconfirm --noconsole --onefile `
      --collect-all runicorn `
      --collect-all uvicorn `
      --collect-all paramiko `
      --collect-all cryptography `
      --collect-all multipart `
      --collect-all python_multipart `
      --collect-submodules multipart `
      --hidden-import ssl --hidden-import _ssl --hidden-import _hashlib --hidden-import _bz2 --hidden-import _lzma `
      --hidden-import multipart --hidden-import python_multipart --hidden-import python_multipart.multipart `
      @addBinArgs `
      --name runicorn-viewer `
      (Join-Path $here "run_viewer_app.py")
    # restore
    foreach ($k in $backup.Keys) { [System.Environment]::SetEnvironmentVariable($k, $backup[$k]) }
  } finally {
    $env:PATH = $oldPath
  }

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
