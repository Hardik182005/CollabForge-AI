# Creatrix Studio (Track 2) — deploy backend to Cloud Run + frontend to Firebase
# Run: ./deploy.ps1   (from the track2 folder)
Set-Location $PSScriptRoot

$PROJECT = "mediflow-nexus-2026"
$REGION  = "us-central1"
$SERVICE = "creatrix-studio"
$SITE    = "creatrix-studio"

Write-Host "=== Creatrix Studio (Track 2) Deploy ===" -ForegroundColor Cyan

# 1. Read .env keys (skip placeholders)
$envFile = Join-Path $PSScriptRoot "backend\.env"
$envVars = @{}
Get-Content $envFile | Where-Object { $_ -match "^\s*[^#].+=.+" } | ForEach-Object {
    $parts = $_ -split "=", 2
    $key   = $parts[0].Trim()
    $value = $parts[1].Trim()
    if ($value -and $value -ne "" -and -not $value.StartsWith("...") -and -not $value.StartsWith("sk-...")) {
        $envVars[$key] = $value
    }
}
$envVars["APP_ENV"] = "production"
$envVars.Remove("PORT") | Out-Null
$envStr = ($envVars.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ","

Write-Host "[1/4] Deploying backend to Cloud Run ($SERVICE)..." -ForegroundColor Yellow
$deployArgs = @(
    "run", "deploy", $SERVICE,
    "--source=.",
    "--region=$REGION",
    "--project=$PROJECT",
    "--allow-unauthenticated",
    "--port=8080",
    "--memory=1Gi",
    "--cpu=1",
    "--min-instances=0",
    "--max-instances=3",
    "--clear-base-image",
    "--set-env-vars=$envStr"
)
& gcloud @deployArgs
if ($LASTEXITCODE -ne 0) { Write-Host "Cloud Run deploy failed." -ForegroundColor Red; exit 1 }

Write-Host "[2/4] Getting Cloud Run service URL..." -ForegroundColor Yellow
$SERVICE_URL = & gcloud run services describe $SERVICE --region=$REGION --project=$PROJECT --format="value(status.url)" 2>&1
Write-Host "Backend URL: $SERVICE_URL" -ForegroundColor Green

Write-Host "[3/4] Ensuring Firebase Hosting site '$SITE' exists..." -ForegroundColor Yellow
& firebase hosting:sites:create $SITE --project=$PROJECT 2>$null
@"
{
  "projects": {
    "default": "$PROJECT"
  }
}
"@ | Set-Content ".firebaserc" -Encoding utf8

Write-Host "[4/4] Deploying frontend to Firebase Hosting ($SITE)..." -ForegroundColor Yellow
& firebase deploy --only hosting --project=$PROJECT
if ($LASTEXITCODE -ne 0) { Write-Host "Firebase deploy failed." -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "=== CREATRIX STUDIO DEPLOY COMPLETE ===" -ForegroundColor Green
Write-Host "Backend  : $SERVICE_URL"  -ForegroundColor Cyan
Write-Host "Frontend : https://$SITE.web.app" -ForegroundColor Cyan
Write-Host "Docs     : $SERVICE_URL/docs" -ForegroundColor Cyan
