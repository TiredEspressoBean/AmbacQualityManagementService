# Setup pgvector extension on PostgreSQL (PowerShell version)

$ErrorActionPreference = "Stop"

$RESOURCE_GROUP = "PartsTracker"
$POSTGRES_SERVER = "parts-tracker-django-server"
$POSTGRES_DB = "parts-tracker-django-database"
$POSTGRES_USER = "kdezfhzdbd"

Write-Host "Setting up pgvector extension on PostgreSQL..." -ForegroundColor Green
Write-Host ""

# Step 1: Enable pgvector at server level
Write-Host "1. Enabling pgvector extension at server level..." -ForegroundColor Cyan
az postgres flexible-server parameter set `
    --resource-group $RESOURCE_GROUP `
    --server-name $POSTGRES_SERVER `
    --name azure.extensions `
    --value "VECTOR" `
    --output none

Write-Host "   ✓ Extension enabled at server level" -ForegroundColor Green
Write-Host ""

# Step 2: Install in database
Write-Host "2. Installing pgvector extension in database..." -ForegroundColor Cyan
Write-Host "   You need to provide the PostgreSQL admin password" -ForegroundColor Yellow
Write-Host ""

$POSTGRES_HOST = "$POSTGRES_SERVER.postgres.database.azure.com"

$POSTGRES_PASSWORD = Read-Host "PostgreSQL password" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($POSTGRES_PASSWORD)
$POSTGRES_PASSWORD_PLAIN = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

$env:PGPASSWORD = $POSTGRES_PASSWORD_PLAIN

try {
    psql -h $POSTGRES_HOST `
        -U $POSTGRES_USER `
        -d $POSTGRES_DB `
        -c "CREATE EXTENSION IF NOT EXISTS vector;"

    Write-Host "   ✓ pgvector extension installed successfully!" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Failed to install extension. Make sure psql is installed and credentials are correct." -ForegroundColor Red
    Write-Host "   Error: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Done! You can verify by running:" -ForegroundColor Green
Write-Host "  psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c '\dx'" -ForegroundColor White
