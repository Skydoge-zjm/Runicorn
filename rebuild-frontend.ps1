# Frontend rebuild script

# Build frontend
Write-Host "Building frontend..." -ForegroundColor Cyan
npm --prefix web/frontend run build

if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend build failed!" -ForegroundColor Red
    exit 1
}

# Clean old files
Write-Host "Cleaning old files..." -ForegroundColor Cyan
Remove-Item -Path "src\runicorn\webui" -Recurse -Force -ErrorAction SilentlyContinue

# Create directory
New-Item -Path "src\runicorn\webui" -ItemType Directory -Force | Out-Null

# Copy new files
Write-Host "Copying build files..." -ForegroundColor Cyan
Copy-Item -Path "web\frontend\dist\*" -Destination "src\runicorn\webui\" -Recurse -Force

# Start viewer
Write-Host "Starting runicorn viewer..." -ForegroundColor Green
runicorn viewer
