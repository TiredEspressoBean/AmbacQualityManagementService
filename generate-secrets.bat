@echo off
REM Script to generate secure environment variables for Parts Tracker (Windows)

echo 🔐 Generating secure environment variables for Parts Tracker

REM Environment selection
echo Select environment:
echo 1) Local Development
echo 2) Local Production
echo 3) Azure Production
set /p choice=Enter choice (1-3): 

if "%choice%"=="1" (
    set ENV_FILE=.env.local
    set ENV_NAME=Local Development
) else if "%choice%"=="2" (
    set ENV_FILE=.env.prod.local
    set ENV_NAME=Local Production
) else if "%choice%"=="3" (
    set ENV_FILE=.env.production
    set ENV_NAME=Azure Production
) else (
    echo Invalid choice. Exiting.
    exit /b 1
)

echo 📝 Generating secrets for %ENV_NAME% environment...

REM Generate secrets using PowerShell
for /f %%i in ('powershell -command "[System.Web.Security.Membership]::GeneratePassword(50, 10)"') do set DJANGO_SECRET=%%i
for /f %%i in ('powershell -command "[System.Web.Security.Membership]::GeneratePassword(24, 5)"') do set POSTGRES_PASSWORD=%%i
for /f %%i in ('powershell -command "[System.Web.Security.Membership]::GeneratePassword(24, 5)"') do set POWERBI_PASSWORD=%%i

REM Create backup if file exists
if exist "%ENV_FILE%" (
    set backup_name=%ENV_FILE%.backup.%date:~-4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
    copy "%ENV_FILE%" "%backup_name%" >nul
    echo 📋 Backed up existing %ENV_FILE%
)

REM Base configuration based on environment
if "%choice%"=="1" (
    (
        echo # Local Development Environment Configuration
        echo # Generated on %date% %time%
        echo.
        echo # Django Configuration
        echo DJANGO_SECRET_KEY=%DJANGO_SECRET%
        echo DJANGO_DEBUG=True
        echo DJANGO_SETTINGS_MODULE=PartsTrackerApp.settings
        echo.
        echo # Database Configuration ^(local PostgreSQL via Docker^)
        echo POSTGRES_DB=parts_tracker_dev
        echo POSTGRES_USER=parts_tracker_user
        echo POSTGRES_PASSWORD=%POSTGRES_PASSWORD%
        echo POSTGRES_HOST=localhost
        echo POSTGRES_PORT=5432
        echo.
        echo # Frontend Configuration
        echo VITE_API_TARGET=http://localhost:8000
        echo.
        echo # Local Host Configuration
        echo ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,backend
        echo CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8080
        echo.
        echo # Development Settings
        echo # Email backend for development ^(prints to console^)
        echo EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
        echo.
        echo # Security Settings ^(relaxed for development^)
        echo SECURE_SSL_REDIRECT=False
        echo SESSION_COOKIE_SECURE=False
        echo CSRF_COOKIE_SECURE=False
        echo.
        echo # Power BI Integration
        echo POWERBI_PASSWORD=%POWERBI_PASSWORD%
    ) > "%ENV_FILE%"
) else if "%choice%"=="2" (
    set /p SERVER_IP=Enter your Linux server IP: 
    (
        echo # Local Production Testing Environment Configuration
        echo # Generated on %date% %time%
        echo.
        echo # Django Configuration
        echo DJANGO_SECRET_KEY=%DJANGO_SECRET%
        echo DJANGO_DEBUG=False
        echo DJANGO_SETTINGS_MODULE=PartsTrackerApp.settings_azure
        echo.
        echo # Database Configuration ^(local PostgreSQL for production testing^)
        echo POSTGRES_DB=parts_tracker_prod_test
        echo POSTGRES_USER=parts_tracker_user
        echo POSTGRES_PASSWORD=%POSTGRES_PASSWORD%
        echo POSTGRES_HOST=postgres
        echo POSTGRES_PORT=5432
        echo.
        echo # Frontend Configuration
        echo VITE_API_TARGET=http://!SERVER_IP!:8000
        echo.
        echo # Local Production Host Configuration
        echo ALLOWED_HOSTS=!SERVER_IP!,localhost,127.0.0.1,backend,frontend
        echo CORS_ALLOWED_ORIGINS=http://!SERVER_IP!,http://!SERVER_IP!:80,http://!SERVER_IP!:8080
        echo.
        echo # Production-like Email Configuration ^(optional - use console for testing^)
        echo EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
        echo.
        echo # Security Settings ^(production-like but adapted for local testing^)
        echo SECURE_SSL_REDIRECT=False
        echo SESSION_COOKIE_SECURE=False
        echo CSRF_COOKIE_SECURE=False
        echo.
        echo # Power BI Integration
        echo POWERBI_PASSWORD=%POWERBI_PASSWORD%
    ) > "%ENV_FILE%"
) else if "%choice%"=="3" (
    set /p BACKEND_FQDN=Enter your backend FQDN: 
    set /p FRONTEND_FQDN=Enter your frontend FQDN: 
    set /p POSTGRES_SERVER=Enter your PostgreSQL server name: 
    (
        echo # Production Environment Variables for Azure Container Apps
        echo # Generated on %date% %time%
        echo.
        echo # Django Configuration
        echo DJANGO_SECRET_KEY=%DJANGO_SECRET%
        echo DJANGO_DEBUG=False
        echo DJANGO_SETTINGS_MODULE=PartsTrackerApp.settings_azure
        echo.
        echo # Database Configuration ^(Azure Database for PostgreSQL Flexible Server^)
        echo POSTGRES_DB=parts_tracker
        echo POSTGRES_USER=parts_tracker_user
        echo POSTGRES_PASSWORD=%POSTGRES_PASSWORD%
        echo POSTGRES_HOST=!POSTGRES_SERVER!.postgres.database.azure.com
        echo POSTGRES_PORT=5432
        echo.
        echo # Allowed Hosts
        echo ALLOWED_HOSTS=!BACKEND_FQDN!,localhost,127.0.0.1
        echo.
        echo # CORS Configuration
        echo CORS_ALLOWED_ORIGINS=https://!FRONTEND_FQDN!
        echo.
        echo # Frontend Configuration
        echo VITE_API_TARGET=https://!BACKEND_FQDN!
        echo.
        echo # Security Settings
        echo SECURE_SSL_REDIRECT=True
        echo SECURE_BROWSER_XSS_FILTER=True
        echo SECURE_CONTENT_TYPE_NOSNIFF=True
        echo SESSION_COOKIE_SECURE=True
        echo CSRF_COOKIE_SECURE=True
        echo.
        echo # Power BI Integration
        echo POWERBI_PASSWORD=%POWERBI_PASSWORD%
    ) > "%ENV_FILE%"
)

echo ✅ Environment file %ENV_FILE% created successfully!
echo.
echo 🔒 Generated secrets:
echo    Django Secret Key: [HIDDEN - 50 characters]
echo    PostgreSQL Password: [HIDDEN - 24 characters]
echo    Power BI Password: [HIDDEN - 24 characters]
echo.
echo 📋 Next steps:
echo    1. Review and customize %ENV_FILE% as needed
echo    2. Never commit this file to version control
echo    3. Share secrets securely with your team
echo    4. Set up backup/recovery for these credentials
echo.
echo 🔐 Security reminders:
echo    - Store backup of secrets in secure password manager
echo    - Rotate passwords regularly
echo    - Use different passwords for each environment
echo    - Monitor access logs for unauthorized usage

pause