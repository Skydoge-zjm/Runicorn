param(
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

# Install deps
python -m pip install -r "$PSScriptRoot/requirements.txt"

# Move to project root to ensure imports
Push-Location (Resolve-Path "$PSScriptRoot/../..")
try {
  # Let uvicorn import the src package layout
  $env:PYTHONPATH = "$PWD/src;$env:PYTHONPATH"
  python -X utf8 -m uvicorn runicorn.viewer:create_app --factory --reload --host 127.0.0.1 --port $Port
} finally {
  Pop-Location
}
