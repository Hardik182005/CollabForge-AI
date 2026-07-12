# CollabForge AI — backend deployment (PowerShell wrapper)
# Requires Git Bash (ships with Git for Windows), Docker Desktop and AWS CLI.
$ErrorActionPreference = "Stop"
$bash = (Get-Command bash -ErrorAction SilentlyContinue).Source
if (-not $bash) { $bash = "C:\Program Files\Git\bin\bash.exe" }
if (-not (Test-Path $bash)) { Write-Error "Git Bash not found — install Git for Windows"; exit 1 }
& $bash "$PSScriptRoot/deploy_backend_aws.sh"
exit $LASTEXITCODE
