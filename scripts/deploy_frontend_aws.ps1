# CollabForge AI — frontend deployment (PowerShell wrapper)
# Usage: $env:BACKEND_URL="https://xxxx.awsapprunner.com"; ./scripts/deploy_frontend_aws.ps1
$ErrorActionPreference = "Stop"
if (-not $env:BACKEND_URL) { Write-Error "Set BACKEND_URL first"; exit 1 }
$bash = (Get-Command bash -ErrorAction SilentlyContinue).Source
if (-not $bash) { $bash = "C:\Program Files\Git\bin\bash.exe" }
if (-not (Test-Path $bash)) { Write-Error "Git Bash not found — install Git for Windows"; exit 1 }
& $bash "$PSScriptRoot/deploy_frontend_aws.sh"
exit $LASTEXITCODE
