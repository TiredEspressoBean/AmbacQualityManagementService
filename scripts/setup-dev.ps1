<#
.SYNOPSIS
    Starts PostgreSQL and Redis for local development.
    Reads database credentials from .env file.

.EXAMPLE
    .\scripts\setup-dev.ps1
#>

$projectRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $projectRoot ".env"

# Load .env file
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim())
        }
    }
}

# Get values with defaults
$POSTGRES_DB = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "tracker_AMBAC" }
$POSTGRES_USER = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "postgres" }
$POSTGRES_PASSWORD = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { "postgres" }

Write-Host "`nStarting dev databases..." -ForegroundColor Cyan

# Start postgres with pgvector
$pgRunning = docker ps -q -f name=partstracker-postgres
if ($pgRunning) {
    Write-Host "PostgreSQL already running" -ForegroundColor Gray
} else {
    # Remove stopped container if exists
    docker rm partstracker-postgres 2>&1 | Out-Null
    docker run -d `
        --name partstracker-postgres `
        -p 5432:5432 `
        -e POSTGRES_DB=$POSTGRES_DB `
        -e POSTGRES_USER=$POSTGRES_USER `
        -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD `
        -v partstracker_pgdata:/var/lib/postgresql/data `
        ankane/pgvector:v0.5.1 | Out-Null
    Write-Host "Started PostgreSQL" -ForegroundColor Green
}

# Start redis
$redisRunning = docker ps -q -f name=partstracker-redis
if ($redisRunning) {
    Write-Host "Redis already running" -ForegroundColor Gray
} else {
    docker rm partstracker-redis 2>&1 | Out-Null
    docker run -d `
        --name partstracker-redis `
        -p 6379:6379 `
        redis:7-alpine | Out-Null
    Write-Host "Started Redis" -ForegroundColor Green
}

# Wait for postgres to be ready
Write-Host "Waiting for PostgreSQL..." -ForegroundColor Gray
$attempt = 0
do {
    Start-Sleep -Seconds 2
    $attempt++
    docker exec partstracker-postgres pg_isready -U $POSTGRES_USER 2>&1 | Out-Null
} while ($LASTEXITCODE -ne 0 -and $attempt -lt 15)

# Wait for database to be created
$attempt = 0
do {
    Start-Sleep -Seconds 1
    $attempt++
    $dbExists = docker exec partstracker-postgres psql -U $POSTGRES_USER -lqt 2>&1 | Select-String $POSTGRES_DB
} while (-not $dbExists -and $attempt -lt 10)

# Create extensions
docker exec partstracker-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>&1 | Out-Null
cmd /c "docker exec partstracker-postgres psql -U $POSTGRES_USER -d $POSTGRES_DB -c `"CREATE EXTENSION IF NOT EXISTS \`"uuid-ossp\`";`"" 2>&1 | Out-Null

Write-Host "`nReady:" -ForegroundColor Green
Write-Host "  PostgreSQL: localhost:5432 (db: $POSTGRES_DB, user: $POSTGRES_USER)"
Write-Host "  Redis:      localhost:6379"
Write-Host "`nNext: cd PartsTracker && python manage.py migrate && python manage.py runserver`n"
