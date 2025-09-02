param(
  [string]$PythonExe = "E:\Anaconda\envs\pytorch\python.exe",
  [int]$BackendPort = 8000,
  [int]$FrontendPort = 5173,
  [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

if (-not (Test-Path $PythonExe)) {
  Write-Warning "Python not found at $PythonExe. Falling back to 'python' from PATH."
  $PythonExe = "python"
}

# --- Helpers ---
# Robust port check (supports IPv4/IPv6; silent; tries localhost and 127.0.0.1)
function Wait-Port([int]$Port, [int]$TimeoutSec = 120) {
  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  $hosts = @('127.0.0.1','localhost')
  while ((Get-Date) -lt $deadline) {
    foreach ($h in $hosts) {
      try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect($h, $Port, $null, $null)
        if ($iar.AsyncWaitHandle.WaitOne(300) -and $client.Connected) {
          $client.EndConnect($iar) | Out-Null
          $client.Dispose()
          return $true
        }
        $client.Close()
      } catch {}
    }
    Start-Sleep -Milliseconds 300
  }
  return $false
}

# --- Start backend in a new PowerShell window ---
$backendCmd = @"
`$ErrorActionPreference = 'Stop'
Set-Location '$Root'
`$env:PYTHONUTF8 = '1'
`$env:PYTHONIOENCODING = 'utf-8:backslashreplace'
& '$PythonExe' -m pip install -r 'web/backend/requirements.txt'
# Ensure src-based package imports work for uvicorn
`$env:PYTHONPATH = "$Root/src;`$env:PYTHONPATH"
& '$PythonExe' -X utf8 -m uvicorn runicorn.viewer:create_app --factory --host 127.0.0.1 --port $BackendPort --reload
"@

Start-Process -FilePath "powershell" -ArgumentList "-NoExit","-NoLogo","-Command",$backendCmd -WorkingDirectory $Root | Out-Null

Write-Host "Waiting for backend to be ready at http://127.0.0.1:$BackendPort ..."
if (Wait-Port -Port $BackendPort -TimeoutSec 180) {
  Write-Host "Backend is ready."
} else {
  Write-Warning "Backend was not reachable within timeout. Starting frontend anyway."
}

# --- Start frontend in a new PowerShell window ---
$frontendCmd = @"
`$ErrorActionPreference = 'Stop'
Push-Location '$Root/web/frontend'
try {
  if (-Not (Test-Path 'node_modules')) { npm install }
  `$env:PORT = '$FrontendPort'
  # Force Vite to bind to IPv4 and the specified port for reliable health-checks
  npm run dev -- --port $FrontendPort --host 127.0.0.1
} finally { Pop-Location }
"@

Start-Process -FilePath "powershell" -ArgumentList "-NoExit","-NoLogo","-Command",$frontendCmd -WorkingDirectory $Root | Out-Null

# --- Optionally open the browser when frontend is ready ---
# (Wait-Port is defined in Helpers section above)

if (-not $NoBrowser) {
  if (Wait-Port -Port $FrontendPort -TimeoutSec 60) {
    Start-Process "http://localhost:$FrontendPort"
  } else {
    Write-Host "Frontend not reachable yet at http://127.0.0.1:$FrontendPort"
  }
}
