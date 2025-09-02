param(
  [ValidateSet("patch","minor","major")] [string]$Bump = "patch",
  [string]$NewVersion,
  [ValidateSet("testpypi","pypi")] [string]$Repository = "testpypi",
  [string]$PythonExe = "python",
  [switch]$NoBuildFrontend,
  [switch]$NoUpload
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

function Require-Cmd([string]$Cmd) {
  $x = Get-Command $Cmd -ErrorAction SilentlyContinue
  if (-not $x) { throw "Command not found: $Cmd" }
}

# Write text file as UTF-8 without BOM to satisfy tomli/tomllib
function Set-FileUtf8NoBom([string]$Path, [string]$Text) {
  $enc = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $Text, $enc)
}

Require-Cmd $PythonExe
if (-not $NoBuildFrontend) { Require-Cmd "npm" }

# 1) Build frontend (unless skipped)
if (-not $NoBuildFrontend) {
  Push-Location (Join-Path $Root "web/frontend")
  try {
    if (-Not (Test-Path "node_modules")) { npm ci }
    npm run build
  } finally { Pop-Location }

  # Copy dist -> src/runicorn/webui
  $uiDir = Join-Path $Root "src/runicorn/webui"
  Remove-Item -Recurse -Force $uiDir -ErrorAction Ignore
  New-Item -ItemType Directory $uiDir | Out-Null
  Copy-Item -Recurse -Force (Join-Path $Root "web/frontend/dist/*") $uiDir
}

# 2) Bump version in pyproject.toml
$pyproj = Join-Path $Root "pyproject.toml"
if (-not (Test-Path $pyproj)) { throw "pyproject.toml not found at $pyproj" }

$content = Get-Content $pyproj -Raw -Encoding UTF8
$verMatch = [regex]::Match($content, '(?ms)^\s*version\s*=\s*"(?<v>\d+\.\d+\.\d+)"')
if (-not $verMatch.Success) { throw "Cannot find version in pyproject.toml" }
$cur = $verMatch.Groups["v"].Value

if ($NewVersion) {
  $next = $NewVersion
} else {
  $parts = $cur.Split('.')
  $maj = [int]$parts[0]; $min = [int]$parts[1]; $pat = [int]$parts[2]
  switch ($Bump) {
    "major" { $maj += 1; $min = 0; $pat = 0 }
    "minor" { $min += 1; $pat = 0 }
    default { $pat += 1 }
  }
  $next = "$maj.$min.$pat"
}

$content = [regex]::Replace($content, '(?ms)^\s*version\s*=\s*"(\d+\.\d+\.\d+)"', "version = `"$next`"")
Set-FileUtf8NoBom -Path $pyproj -Text $content
Write-Host "Version bumped: $cur -> $next"

# 3) Clean outputs
Remove-Item -Recurse -Force (Join-Path $Root "dist") -ErrorAction Ignore
Remove-Item -Recurse -Force (Join-Path $Root "build") -ErrorAction Ignore

# 4) Build sdist + wheel
& $PythonExe -m build
if ($LASTEXITCODE -ne 0) { throw "Build failed. See errors above." }
# Ensure artifacts exist
$distDir = Join-Path $Root "dist"
if (-not (Test-Path $distDir)) { throw "dist/ not found after build" }
$artifacts = Get-ChildItem -Path $distDir -File -ErrorAction SilentlyContinue
if (-not $artifacts) { throw "No artifacts in dist/. Build likely failed." }

# 5) Twine check
& $PythonExe -m twine check (Join-Path $Root "dist/*")
if ($LASTEXITCODE -ne 0) { throw "twine check failed." }

# 6) Upload
if (-not $NoUpload) {
  $repoArgs = @()
  if ($Repository -eq "testpypi") { $repoArgs = @("--repository", "testpypi") }
  & $PythonExe -m twine upload @repoArgs (Join-Path $Root "dist/*")
  if ($LASTEXITCODE -ne 0) { throw "twine upload failed." }
  Write-Host "Uploaded to $Repository. Version: $next"
  if ($Repository -eq "testpypi") {
    Write-Host "Install test build:"
    Write-Host "  pip install -i https://test.pypi.org/simple/ runicorn==$next --extra-index-url https://pypi.org/simple"
  } else {
    Write-Host "Install: pip install runicorn==$next"
  }
} else {
  Write-Host "Build complete. Upload skipped. Artifacts are in dist/"
}
