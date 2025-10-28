#!/usr/bin/env pwsh
# Test Frontend Build Script
# Validates that the new Remote Viewer frontend can compile successfully

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Frontend Build Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Change to frontend directory
Set-Location $PSScriptRoot

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host "⚠️  node_modules not found. Installing dependencies..." -ForegroundColor Yellow
    npm install
}

Write-Host "🔨 Building frontend..." -ForegroundColor Green
npm run build

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Build successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Build Statistics:" -ForegroundColor Cyan
    
    # Check dist directory
    if (Test-Path "dist") {
        $distSize = (Get-ChildItem -Recurse "dist" | Measure-Object -Property Length -Sum).Sum
        $distSizeMB = [math]::Round($distSize / 1MB, 2)
        Write-Host "  Dist size: $distSizeMB MB" -ForegroundColor White
        
        $fileCount = (Get-ChildItem -Recurse "dist" -File | Measure-Object).Count
        Write-Host "  Files: $fileCount" -ForegroundColor White
    }
    
    Write-Host ""
    Write-Host "🎯 Next Steps:" -ForegroundColor Cyan
    Write-Host "  1. Copy to Python package:" -ForegroundColor White
    Write-Host "     Remove-Item -Recurse -Force ../../src/runicorn/webui" -ForegroundColor Gray
    Write-Host "     mkdir ../../src/runicorn/webui" -ForegroundColor Gray
    Write-Host "     Copy-Item -Recurse dist/* ../../src/runicorn/webui/" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  2. Start Runicorn Viewer:" -ForegroundColor White
    Write-Host "     runicorn viewer" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  3. Access Remote Viewer:" -ForegroundColor White
    Write-Host "     http://localhost:23300/remote" -ForegroundColor Gray
    Write-Host ""
    
} else {
    Write-Host ""
    Write-Host "❌ Build failed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  - Missing dependencies: npm install" -ForegroundColor White
    Write-Host "  - TypeScript errors: Check compilation output above" -ForegroundColor White
    Write-Host "  - Import errors: Verify all file paths" -ForegroundColor White
    Write-Host ""
    exit 1
}
