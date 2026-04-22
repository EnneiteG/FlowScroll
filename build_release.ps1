# Build script to create a single-file Windows executable and put it into ./release
# Usage: Open PowerShell, cd to the project folder and run: .\build_release.ps1
# The main local test artifact is .\release\FlowScroll.exe.
# Use that executable to validate new builds quickly without reinstalling the app.

param(
    [switch]$NoInstall
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $root

$releaseDir = Join-Path $root 'release'
$distExeName = 'FlowScroll.exe'

Write-Host "Cleaning release folder while preserving the local test target path..."
if (Test-Path $releaseDir) {
    Get-ChildItem -Path $releaseDir -Recurse -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
} else {
    New-Item -ItemType Directory -Path $releaseDir | Out-Null
}

if (-not $NoInstall) {
    Write-Host "Ensuring PyInstaller is installed (this may take a moment)..."
    python -m pip install --upgrade pip
    python -m pip install --upgrade pyinstaller
}

# Build with the versioned PyInstaller spec file
Write-Host "Running PyInstaller with versioned FlowScroll.spec..."
pyinstaller FlowScroll.spec --clean --noconfirm

$built = Join-Path $root 'dist' | Join-Path -ChildPath $distExeName
if (-not (Test-Path $built)) {
    # support join variant
    $built = Join-Path (Join-Path $root 'dist') $distExeName
}

if (Test-Path $built) {
    Write-Host "Copying executable to release folder for local testing..."
    Copy-Item $built -Destination (Join-Path $releaseDir $distExeName) -Force
    Write-Host "Cleaning intermediate PyInstaller files..."
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "build","dist"
    Write-Host "Local test build ready: $($releaseDir)\$distExeName"
} else {
    Write-Error "Build failed: executable not found in dist/. Check PyInstaller output above."
}
