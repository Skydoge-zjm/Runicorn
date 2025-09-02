param(
  [int]$Port = 5173
)

$ErrorActionPreference = "Stop"

Push-Location $PSScriptRoot
try {
  if (-Not (Test-Path package-lock.json)) {
    Write-Host "Installing npm dependencies..."
    npm install
  }
  Write-Host "Starting Vite dev server on port $Port..."
  $env:PORT = "$Port"
  npm run dev
}
finally {
  Pop-Location
}
