@echo off
REM Generate init.sql from template using environment variables
REM Usage: generate-init-sql.bat

setlocal

REM Set defaults for environment variables if not set
if not defined POSTGRES_DB set POSTGRES_DB=tracker_AMBAC
if not defined POSTGRES_READONLY_USER set POSTGRES_READONLY_USER=readonly_user
if not defined POSTGRES_READONLY_PASSWORD set POSTGRES_READONLY_PASSWORD=readonly_pw

echo Generating init.sql from template...
echo Using database: %POSTGRES_DB%
echo Using readonly user: %POSTGRES_READONLY_USER%

REM Check if template exists
if not exist "init.sql.template" (
    echo Error: init.sql.template not found!
    exit /b 1
)

REM Generate init.sql from template using PowerShell for variable substitution
powershell -Command "(Get-Content 'init.sql.template') -replace '\${POSTGRES_DB}', '%POSTGRES_DB%' -replace '\${POSTGRES_READONLY_USER}', '%POSTGRES_READONLY_USER%' -replace '\${POSTGRES_READONLY_PASSWORD}', '%POSTGRES_READONLY_PASSWORD%' | Set-Content 'init.sql'"

echo Successfully generated init.sql
echo.
echo Environment variables used:
echo   POSTGRES_DB=%POSTGRES_DB%
echo   POSTGRES_READONLY_USER=%POSTGRES_READONLY_USER%
echo   POSTGRES_READONLY_PASSWORD=***