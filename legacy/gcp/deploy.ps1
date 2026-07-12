# Creatrix AI — One-click deploy to Google Cloud
# Run: ./deploy.ps1
# Requires: gcloud CLI, firebase CLI, both logged in

# Always run from the repo root so `--source=.` and relative file reads resolve
# correctly regardless of the caller's working directory.
Set-Location $PSScriptRoot

$PROJECT = "mediflow-nexus-2026"
$REGION  = "us-central1"
$SERVICE = "creatrix-ai-backend"
$REPO    = "creatrix-ai"

Write-Host "=== Creatrix AI Deploy ===" -ForegroundColor Cyan

# ── 1. Read .env ──────────────────────────────────────────────────────────────
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

# Always set these
$envVars["APP_ENV"] = "production"

# PORT is a Cloud Run reserved env var (auto-set by the platform) — never pass it.
$envVars.Remove("PORT") | Out-Null

# Build --set-env-vars string (never echoed to screen)
$envStr = ($envVars.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ","

Write-Host "[1/4] Deploying backend to Cloud Run..." -ForegroundColor Yellow

# ── 2. Deploy Cloud Run from source ──────────────────────────────────────────
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

# ── 3. Get the Cloud Run URL ──────────────────────────────────────────────────
Write-Host "[2/4] Getting Cloud Run service URL..." -ForegroundColor Yellow
$SERVICE_URL = & gcloud run services describe $SERVICE --region=$REGION --project=$PROJECT --format="value(status.url)" 2>&1
Write-Host "Backend URL: $SERVICE_URL" -ForegroundColor Green

# ── 4. Update firebase.json with real service ID ──────────────────────────────
Write-Host "[3/4] Configuring Firebase Hosting rewrite to Cloud Run..." -ForegroundColor Yellow
$firebaseJson = Get-Content "firebase.json" -Raw | ConvertFrom-Json
$firebaseJson.hosting.rewrites[0].run.serviceId = $SERVICE
$firebaseJson | ConvertTo-Json -Depth 10 | Set-Content "firebase.json" -Encoding utf8

# Write .firebaserc
@"
{
  "projects": {
    "default": "$PROJECT"
  }
}
"@ | Set-Content ".firebaserc" -Encoding utf8

# ── 5. Deploy Firebase Hosting ─────────────────────────────────────────────────
Write-Host "[4/4] Deploying frontend to Firebase Hosting..." -ForegroundColor Yellow
& firebase deploy --only hosting --project=$PROJECT
if ($LASTEXITCODE -ne 0) { Write-Host "Firebase deploy failed." -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "=== DEPLOY COMPLETE ===" -ForegroundColor Green
Write-Host "Backend  : $SERVICE_URL"  -ForegroundColor Cyan
Write-Host "Frontend : https://$PROJECT.web.app" -ForegroundColor Cyan
Write-Host "Docs     : $SERVICE_URL/docs" -ForegroundColor Cyan
