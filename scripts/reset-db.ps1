<#
.SYNOPSIS
    Resets the PostgreSQL database for local development.

.EXAMPLE
    .\reset-db.ps1
#>

Write-Host "`nResetting database..." -ForegroundColor Cyan

# Stop and remove postgres container
docker stop partstracker-postgres 2>&1 | Out-Null
docker rm partstracker-postgres 2>&1 | Out-Null

# Remove volume
docker volume rm partstracker_pgdata 2>&1 | Out-Null

Write-Host "Removed old container and data" -ForegroundColor Gray

# Restart using setup script
$scriptPath = Join-Path $PSScriptRoot "setup-dev.ps1"
& $scriptPath
