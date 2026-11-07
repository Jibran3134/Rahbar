[CmdletBinding()]
param([int]$Port = 8090, [switch]$NoBrowser, [switch]$CheckOnly, [switch]$Rebuild)
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path $PSScriptRoot -Parent
Push-Location $RepoRoot
try {
    foreach ($Required in @('git', 'docker', 'kubectl', 'ollama')) {
        if (-not (Get-Command $Required -ErrorAction SilentlyContinue)) {
            throw "Install $Required first. See README Windows prerequisites."
        }
    }
    $Python = Join-Path $RepoRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $Python)) {
        & py -3.12 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 first.' }
    }
    & $Python -c "import importlib.util, sys; sys.exit(0 if all(importlib.util.find_spec(m) for m in ('httpx', 'yaml')) else 1)"
    if ($LASTEXITCODE -ne 0) {
        & $Python -m pip install -r api/requirements-dev.txt -r indexer/requirements-dev.txt
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    }
    if (-not (Test-Path '.venv/tools/bin/minikube.exe') -and -not (Test-Path '.venv/tools/minikube.exe')) {
        & $Python scripts/bootstrap_tools.py minikube
        if ($LASTEXITCODE -ne 0) { throw 'Verified minikube installation failed.' }
    }
    $LaunchArgs = @('scripts/run_app.py', '--port', "$Port")
    if ($NoBrowser) { $LaunchArgs += '--no-browser' }
    if ($CheckOnly) { $LaunchArgs += '--check-only' }
    if ($Rebuild) { $LaunchArgs += '--rebuild' }
    & $Python @LaunchArgs
    if ($LASTEXITCODE -ne 0) { throw "App launcher exited with status $LASTEXITCODE" }
} finally { Pop-Location }
