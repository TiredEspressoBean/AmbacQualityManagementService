@echo off
REM Quick start script for local development (Windows)

echo 🚀 Starting Parts Tracker Local Development Environment

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker and try again.
    exit /b 1
)

REM Create .env file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file from template...
    copy .env.local .env
    echo ✅ Created .env file. You may want to customize it for your setup.
)

REM Start the services
echo 🐳 Starting Docker services...
docker-compose up -d

REM Wait for services to be ready
echo ⏳ Waiting for services to start...
timeout /t 10 /nobreak >nul

echo 🔍 Checking service health...

REM Check database
docker-compose exec -T postgres pg_isready -U parts_tracker_user -d parts_tracker_dev >nul 2>&1
if errorlevel 1 (
    echo ❌ Database is not ready
) else (
    echo ✅ Database is ready
)

echo.
echo 🎉 Local development environment is starting up!
echo.
echo 📱 Frontend: http://localhost:5173
echo 🔧 Backend:  http://localhost:8000
echo 📊 Admin:    http://localhost:8000/admin/
echo 📚 API Docs: http://localhost:8000/api/docs/
echo.
echo 💡 Useful commands:
echo    docker-compose logs -f          # View logs
echo    docker-compose down             # Stop services
echo    docker-compose exec backend python manage.py shell  # Django shell
echo.
echo 🔍 To view logs: docker-compose logs -f

pause