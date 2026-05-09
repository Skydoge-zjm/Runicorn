[CmdletBinding()]
param(
  [string]$PythonExe = "",
  [string]$RunicornVersion = "",
  [switch]$UseLocal
)

$ErrorActionPreference = "Stop"
# PowerShell 5.1 doesn't have $PSStyle; guard usage for compatibility
try { if ($PSStyle) { $PSStyle.OutputRendering = 'PlainText' } } catch {}

Write-Host "==> Building Runicorn sidecar (PyInstaller)" -ForegroundColor Cyan

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $here

try {
  . (Join-Path $here "..\build_config.ps1")
  $buildConfig = Get-RunicornBuildConfig (Resolve-Path (Join-Path $here ".."))
  $proxyBackup = Push-RunicornProxyEnv $buildConfig["common"]
  try {
    if (-not $PythonExe) {
      $PythonExe = [string]$buildConfig["common"]["pythonExe"]
    }
    if (-not $RunicornVersion) {
      $RunicornVersion = [string]$buildConfig["sidecar"]["runicornVersion"]
    }
    $UseLocalBuild = $UseLocal.IsPresent -or [bool]$buildConfig["sidecar"]["useLocal"]

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
    if ($UseLocalBuild) {
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

    $patterns = @($buildConfig["sidecar"]["pyInstaller"]["dllPatterns"])
    $dllSearchDirs = @($baseRoot)
    foreach ($relativeDir in @($buildConfig["sidecar"]["pyInstaller"]["dllSearchSubdirs"])) {
      $dllSearchDirs += (Join-Path $baseRoot $relativeDir)
    }
    foreach ($dir in $dllSearchDirs) {
      Add-DllsFrom $dir $patterns
    }
    if ($addBinArgs.Count -gt 0) {
      Write-Host ("Including base DLLs from: {0}" -f ($dllSearchDirs -join "; ")) -ForegroundColor Yellow
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
    $pyInstallerArgs = @("--noconfirm", "--noconsole", "--onefile")
    foreach ($moduleName in @($buildConfig["sidecar"]["pyInstaller"]["collectAll"])) {
      $pyInstallerArgs += @("--collect-all", $moduleName)
    }
    foreach ($moduleName in @($buildConfig["sidecar"]["pyInstaller"]["collectSubmodules"])) {
      $pyInstallerArgs += @("--collect-submodules", $moduleName)
    }
    foreach ($importName in @($buildConfig["sidecar"]["pyInstaller"]["hiddenImports"])) {
      $pyInstallerArgs += @("--hidden-import", $importName)
    }
    $pyInstallerArgs += $addBinArgs
    $pyInstallerArgs += @("--name", $buildConfig["sidecar"]["pyInstaller"]["name"], (Join-Path $here "run_viewer_app.py"))
    & $venvPy -m PyInstaller @pyInstallerArgs
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

  # 5) Basic runtime verification: start the sidecar and require /api/health
  function Get-FreeTcpPort {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, 0)
    $listener.Start()
    try {
      return ([System.Net.IPEndPoint]$listener.LocalEndpoint).Port
    } finally {
      $listener.Stop()
    }
  }

  $healthPort = Get-FreeTcpPort
    $probeHost = $buildConfig["sidecar"]["runtimeProbe"]["host"]
    $probePath = $buildConfig["sidecar"]["runtimeProbe"]["healthPath"]
  $probeUrl = "http://${probeHost}:$healthPort$probePath"
  $probeProcess = $null
  try {
    Write-Host "Starting sidecar runtime probe on $probeUrl" -ForegroundColor Cyan
    $probeProcess = Start-Process -FilePath $oneFile -ArgumentList @("--host", $probeHost, "--port", "$healthPort") -PassThru -WindowStyle Hidden
    $healthy = $false
      $probeAttempts = [int]$buildConfig["sidecar"]["runtimeProbe"]["attempts"]
      $probeIntervalMs = [int]$buildConfig["sidecar"]["runtimeProbe"]["intervalMs"]
      $probeTimeoutSec = [int]$buildConfig["sidecar"]["runtimeProbe"]["timeoutSec"]
      $probeStatusPattern = [string]$buildConfig["sidecar"]["runtimeProbe"]["statusPattern"]
    for ($i = 0; $i -lt $probeAttempts; $i++) {
      Start-Sleep -Milliseconds $probeIntervalMs
      if ($probeProcess.HasExited) {
        throw "Sidecar exited early during runtime probe with code $($probeProcess.ExitCode)"
      }
      try {
        $resp = Invoke-WebRequest -UseBasicParsing -Uri $probeUrl -TimeoutSec $probeTimeoutSec
        if ($resp.StatusCode -eq 200 -and $resp.Content -match $probeStatusPattern) {
          $healthy = $true
          break
        }
      } catch {
        continue
      }
    }
    if (-not $healthy) {
      throw "Sidecar runtime probe did not reach a healthy response at $probeUrl"
    }
    Write-Host "OK: sidecar runtime probe passed" -ForegroundColor Green
    } finally {
      if ($probeProcess -and -not $probeProcess.HasExited) {
        Stop-Process -Id $probeProcess.Id -Force
        $probeProcess.WaitForExit()
      }
    }
  } finally {
    Pop-RunicornProxyEnv $proxyBackup
  }
}
finally {
  Pop-Location
}
