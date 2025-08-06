# Local Deployment Guide

This guide provides instructions for running your Django + React + PostgreSQL application locally, both for development and production testing.

## Prerequisites

1. **Docker & Docker Compose** installed
   ```bash
   docker --version
   docker-compose --version
   ```

2. **Node.js** (for frontend development)
   ```bash
   node --version
   npm --version
   ```

3. **Python 3.12+** (for backend development)
   ```bash
   python --version
   pip --version
   ```

## Option 1: Local Development (Recommended for Development)

### Step 1: Clone and Setup Environment

```bash
# Clone your repository (if not already done)
git clone <your-repo-url>
cd AmbacTracker

# Create environment file for development
cp .env.production .env.local
```

### Step 2: Configure Local Environment

Edit `.env.local` with local development settings:

```bash
# Django Configuration
DJANGO_SECRET_KEY=your-local-secret-key-for-development-change-this
DJANGO_DEBUG=True
DJANGO_SETTINGS_MODULE=PartsTrackerApp.settings

# Database Configuration (local PostgreSQL)
POSTGRES_DB=parts_tracker_dev
POSTGRES_USER=parts_tracker_user
POSTGRES_PASSWORD=localpassword123-change-this
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Frontend Configuration
VITE_API_TARGET=http://localhost:8000

# Local hosts
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Step 3: Start Development Services

#### Option 3A: Using Docker Compose (Easiest)

```bash
# Start all services with development configuration
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

#### Option 3B: Manual Development Setup (More Control)

**Terminal 1 - Database:**
```bash
# Start PostgreSQL only
docker-compose up -d postgres

# Or use local PostgreSQL installation
```

**Terminal 2 - Backend:**
```bash
cd PartsTracker

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export $(cat ../.env.local | xargs)  # On Windows: set -a; source ../.env.local; set +a

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Install and build Tailwind
python manage.py tailwind install
python manage.py tailwind build

# Start development server
python manage.py runserver 0.0.0.0:8000
```

**Terminal 3 - Frontend:**
```bash
cd ambac-tracker-ui

# Install dependencies
npm install

# Set environment variables
export VITE_API_TARGET=http://localhost:8000

# Start development server
npm run dev
```

### Step 4: Access Your Application

- **Frontend**: http://localhost:5173 (Vite dev server)
- **Backend API**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin/
- **API Documentation**: http://localhost:8000/api/docs/

## Option 2: Local Production Testing

This option runs the production-ready containers locally to test your Azure deployment configuration.

### Step 1: Create Production Environment File

```bash
# Create local production environment
cp .env.production .env.prod.local
```

Edit `.env.prod.local`:

```bash
# Django Configuration
DJANGO_SECRET_KEY=your-strong-secret-key-min-50-chars-for-production-testing-change-this
DJANGO_DEBUG=False
DJANGO_SETTINGS_MODULE=PartsTrackerApp.settings_azure

# Database Configuration (local PostgreSQL)
POSTGRES_DB=parts_tracker_prod
POSTGRES_USER=parts_tracker_user
POSTGRES_PASSWORD=stronglocalpassword123-change-this
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Frontend Configuration
VITE_API_TARGET=http://localhost:8000

# Local hosts for production testing
ALLOWED_HOSTS=localhost,127.0.0.1,backend
CORS_ALLOWED_ORIGINS=http://localhost,http://localhost:80

# Optional: Test Azure storage locally (requires Azure Storage Emulator)
# AZURE_STORAGE_ACCOUNT_NAME=devstoreaccount1
# AZURE_STORAGE_ACCOUNT_KEY=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==
```

### Step 2: Build and Run Production Containers

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start production stack
docker-compose -f docker-compose.prod.yml --env-file .env.prod.local up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Check container health
docker-compose -f docker-compose.prod.yml ps

# Stop production stack
docker-compose -f docker-compose.prod.yml down
```

### Step 3: Initialize Production Database

```bash
# Run migrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Create superuser
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# Collect static files (if not using Azure storage)
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

### Step 4: Access Production Test Environment

- **Frontend**: http://localhost (nginx)
- **Backend API**: http://localhost:8000
- **Reverse Proxy**: http://localhost:8080 (optional nginx proxy)
- **HTTPS**: https://localhost:443 (if SSL certificates configured)

## Option 3: Hybrid Development

Run database in Docker, but Django and React natively for faster development.

### Step 1: Start Database Only

```bash
# Start only PostgreSQL
docker-compose up -d postgres

# Wait for database to be ready
docker-compose exec postgres pg_isready -U parts_tracker_user -d parts_tracker_dev
```

### Step 2: Setup Backend Natively

```bash
cd PartsTracker

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=parts_tracker_dev
export POSTGRES_USER=parts_tracker_user
export POSTGRES_PASSWORD=localpassword123-change-this
export DJANGO_SECRET_KEY=your-dev-secret-key-change-this
export DJANGO_DEBUG=True
export ALLOWED_HOSTS=localhost,127.0.0.1
export CORS_ALLOWED_ORIGINS=http://localhost:5173

# Run Django
python manage.py migrate
python manage.py tailwind install
python manage.py tailwind build
python manage.py runserver
```

### Step 3: Setup Frontend Natively

```bash
cd ambac-tracker-ui

# Install and run
npm install
export VITE_API_TARGET=http://localhost:8000
npm run dev
```

## Environment File Templates

### Development (.env.local)
```bash
# Development Configuration
DJANGO_SECRET_KEY=dev-secret-key-not-for-production
DJANGO_DEBUG=True
DJANGO_SETTINGS_MODULE=PartsTrackerApp.settings

# Local Database
POSTGRES_DB=parts_tracker_dev
POSTGRES_USER=parts_tracker_user
POSTGRES_PASSWORD=localdev123
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Local URLs
VITE_API_TARGET=http://localhost:8000
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8080
```

### Production Testing (.env.prod.local)
```bash
# Production Testing Configuration
DJANGO_SECRET_KEY=your-strong-secret-key-min-50-chars-for-production-testing-change-this
DJANGO_DEBUG=False
DJANGO_SETTINGS_MODULE=PartsTrackerApp.settings_azure

# Local Production Database
POSTGRES_DB=parts_tracker_prod
POSTGRES_USER=parts_tracker_user
POSTGRES_PASSWORD=stronglocalpassword123-change-this
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Local Production URLs
VITE_API_TARGET=http://localhost:8000
ALLOWED_HOSTS=localhost,127.0.0.1,backend,frontend
CORS_ALLOWED_ORIGINS=http://localhost,http://localhost:80
```

## Useful Commands

### Docker Management
```bash
# View running containers
docker ps

# View all containers
docker ps -a

# View container logs
docker logs <container_name>

# Execute command in container
docker exec -it <container_name> bash

# Clean up Docker resources
docker system prune -a
```

### Database Management
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U parts_tracker_user -d parts_tracker_dev

# Backup database
docker-compose exec postgres pg_dump -U parts_tracker_user parts_tracker_dev > backup.sql

# Restore database
docker-compose exec -T postgres psql -U parts_tracker_user -d parts_tracker_dev < backup.sql

# Reset database
docker-compose down -v  # Removes volumes
docker-compose up -d postgres
```

### Django Management
```bash
# Make migrations
docker-compose exec backend python manage.py makemigrations

# Apply migrations
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Django shell
docker-compose exec backend python manage.py shell

# Collect static files
docker-compose exec backend python manage.py collectstatic --noinput

# Tailwind commands
docker-compose exec backend python manage.py tailwind install
docker-compose exec backend python manage.py tailwind build
docker-compose exec backend python manage.py tailwind start  # Watch mode
```

### Frontend Management
```bash
# Install new package
cd ambac-tracker-ui && npm install <package-name>

# Build for production
npm run build

# Type checking
npm run typecheck

# Linting
npm run lint
```

## Troubleshooting

### Common Issues

#### 1. **Port Already in Use**
```bash
# Find process using port
lsof -i :8000  # On Windows: netstat -ano | findstr :8000

# Kill process
kill -9 <PID>  # On Windows: taskkill /PID <PID> /F
```

#### 2. **Database Connection Failed**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres pg_isready -U parts_tracker_user -d parts_tracker_dev
```

#### 3. **Frontend Build Issues**
```bash
# Clear npm cache
npm cache clean --force

# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

#### 4. **Django Static Files Issues**
```bash
# Rebuild Tailwind
docker-compose exec backend python manage.py tailwind build

# Collect static files
docker-compose exec backend python manage.py collectstatic --noinput --clear
```

#### 5. **Permission Issues (Linux/Mac)**
```bash
# Fix file permissions
sudo chown -R $USER:$USER .

# Fix Docker permissions
sudo usermod -aG docker $USER
newgrp docker
```

### Health Checks

#### Check All Services
```bash
# Test backend health
curl http://localhost:8000/health/

# Test frontend health  
curl http://localhost:5173/health  # Development
curl http://localhost/health       # Production

# Test database connection
docker-compose exec postgres pg_isready -U parts_tracker_user -d parts_tracker_dev
```

#### Performance Monitoring
```bash
# Monitor container resources
docker stats

# View container processes
docker-compose top

# Check disk usage
docker system df
```

## Development Workflow

### Daily Development
1. Start services: `docker-compose up -d`
2. Make changes to code
3. Backend auto-reloads (Django development server)
4. Frontend auto-reloads (Vite HMR)
5. Test changes
6. Commit and push

### Before Production Deployment
1. Test locally with production config: `docker-compose -f docker-compose.prod.yml up`
2. Run tests: `npm test` and `python manage.py test`
3. Check for security issues
4. Verify environment variables
5. Deploy to Azure

### Database Schema Changes
1. Make model changes
2. Create migrations: `python manage.py makemigrations`
3. Apply locally: `python manage.py migrate`
4. Test the changes
5. Deploy migrations to production

## VS Code Setup (Optional)

Create `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "./PartsTracker/venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "typescript.preferences.importModuleSpecifier": "relative",
    "editor.formatOnSave": true,
    "docker.defaultRegistryPath": "your-acr-name.azurecr.io"
}
```

Create `.vscode/launch.json` for debugging:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Django Debug",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/PartsTracker/manage.py",
            "args": ["runserver", "0.0.0.0:8000"],
            "django": true,
            "envFile": "${workspaceFolder}/.env.local"
        }
    ]
}
```

---

This guide covers all local development scenarios. Choose the option that best fits your development workflow and requirements.