# Parts Tracker Deployment Guide

This repository contains a Django + React + PostgreSQL application with complete deployment configurations for both local development and Azure Container Apps production deployment.

## 📁 Project Structure

```
AmbacTracker/
├── PartsTracker/                    # Django backend
│   ├── Dockerfile                   # Development Dockerfile
│   ├── Dockerfile.prod             # Production Dockerfile
│   ├── requirements.txt            # Python dependencies
│   └── PartsTrackerApp/
│       ├── settings.py             # Development settings
│       └── settings_azure.py       # Production settings for Azure
├── ambac-tracker-ui/               # React frontend
│   ├── Dockerfile                  # Development Dockerfile
│   ├── Dockerfile.prod            # Production Dockerfile
│   ├── nginx.conf                 # Production nginx config
│   └── package.json               # Node.js dependencies
├── docker-compose.yml             # Development compose
├── docker-compose.override.yml    # Development overrides
├── docker-compose.prod.yml        # Production compose
├── nginx-prod.conf               # Production reverse proxy
├── azure-container-apps.yaml     # Azure Container Apps config
├── .env.local                    # Local development template
├── .env.prod.local              # Local production template
├── .env.production              # Azure production template
├── LOCAL_DEPLOYMENT.md          # Local deployment guide
├── AZURE_DEPLOYMENT.md          # Azure deployment guide
├── start-local.sh              # Quick start (Linux/Mac)
└── start-local.bat            # Quick start (Windows)
```

## 🚀 Quick Start

### For Local Development
```bash
# Step 1: Generate secure environment variables
# Linux/Mac
./generate-secrets.sh

# Windows
generate-secrets.bat

# Step 2: Start development environment
# Linux/Mac
./start-local.sh

# Windows
start-local.bat

# Manual alternative
cp .env.local .env  # Then customize passwords
docker-compose up -d
```

**Access Points:**
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Admin: http://localhost:8000/admin/

### For Azure Production
```bash
# Follow the comprehensive guide
cat AZURE_DEPLOYMENT.md

# Quick deploy (after setup)
az containerapp create --yaml backend-containerapp.yaml
az containerapp create --yaml frontend-containerapp.yaml
```

## 📋 Deployment Options

| Option | Use Case | Guide | Complexity |
|--------|----------|--------|------------|
| **Local Development** | Daily development work (Windows) | [LOCAL_DEPLOYMENT.md](LOCAL_DEPLOYMENT.md) | ⭐ Easy |
| **Local Production** | Test prod configs locally (Windows) | [LOCAL_DEPLOYMENT.md](LOCAL_DEPLOYMENT.md) | ⭐⭐ Medium |
| **Linux Production** | Deploy to Linux server for staging/prod | [LOCAL_LINUX_DEPLOYMENT.md](LOCAL_LINUX_DEPLOYMENT.md) | ⭐⭐⭐ Advanced |
| **Azure Container Apps** | Cloud production deployment | [AZURE_DEPLOYMENT.md](AZURE_DEPLOYMENT.md) | ⭐⭐⭐ Advanced |
| **Power BI Integration** | Connect Power BI to PostgreSQL | [POWER_BI_INTEGRATION.md](POWER_BI_INTEGRATION.md) | ⭐⭐ Medium |

## 🔧 Configuration Files

### Environment Files
- `.env.local` - Local development settings
- `.env.prod.local` - Local production testing
- `.env.production` - Azure production template

### Docker Files
- `Dockerfile` - Development containers (hot reload)
- `Dockerfile.prod` - Production containers (optimized)
- `docker-compose.yml` - Development orchestration
- `docker-compose.prod.yml` - Production orchestration

### Azure Files
- `azure-container-apps.yaml` - Container Apps configuration
- `AZURE_DEPLOYMENT.md` - Complete deployment guide

## 🛠️ Development Workflow

### 1. Daily Development
```bash
# Start development environment
./start-local.sh

# Make changes to code (auto-reload enabled)
# Backend: PartsTracker/
# Frontend: ambac-tracker-ui/

# View logs
docker-compose logs -f

# Stop when done
docker-compose down
```

### 2. Database Changes
```bash
# Create migrations
docker-compose exec backend python manage.py makemigrations

# Apply migrations
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser
```

### 3. Frontend Changes
```bash
# Install new packages
cd ambac-tracker-ui
npm install package-name

# Build for production testing
npm run build

# Type checking
npm run typecheck
```

### 4. Testing Production Locally
```bash
# Test production build locally
docker-compose -f docker-compose.prod.yml --env-file .env.prod.local up -d

# Access at http://localhost
# Test all functionality before Azure deployment
```

### 5. Deploy to Azure
```bash
# Follow Azure deployment guide
cat AZURE_DEPLOYMENT.md

# Build and push images
az acr login --name your-acr
docker build -f PartsTracker/Dockerfile.prod -t your-acr.azurecr.io/backend:latest PartsTracker/
docker push your-acr.azurecr.io/backend:latest

# Deploy containers
az containerapp create --yaml backend-containerapp.yaml
```

## 🔍 Troubleshooting

### Common Issues

#### Port Conflicts
```bash
# Find process using port
lsof -i :8000  # Mac/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>  # Mac/Linux
taskkill /PID <PID> /F  # Windows
```

#### Database Issues
```bash
# Reset local database
docker-compose down -v
docker-compose up -d postgres
docker-compose exec backend python manage.py migrate
```

#### Container Issues
```bash
# Rebuild containers
docker-compose build --no-cache

# Clean Docker system
docker system prune -a
```

## 📚 Detailed Guides

- **[Local Deployment Guide](LOCAL_DEPLOYMENT.md)** - Complete local setup instructions
- **[Linux Deployment Guide](LOCAL_LINUX_DEPLOYMENT.md)** - Linux server deployment
- **[Azure Deployment Guide](AZURE_DEPLOYMENT.md)** - Production deployment on Azure
- **[Power BI Integration](POWER_BI_INTEGRATION.md)** - Database access for Power BI
- **[Security Checklist](SECURITY_CHECKLIST.md)** - Security best practices
- **Environment Configuration** - See template files (`.env.*`)

## 🏛️ Architecture

### Development Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Dev     │    │   Django Dev    │    │   PostgreSQL    │
│   (Vite HMR)    │◄──►│   (Auto-reload) │◄──►│   (Docker)      │
│   Port: 5173    │    │   Port: 8000    │    │   Port: 5432    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Production Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React (nginx) │    │Django (gunicorn)│    │Azure PostgreSQL│
│   Container App │◄──►│  Container App  │◄──►│ Flexible Server │
│   Port: 80      │    │   Port: 8000    │    │   Port: 5432    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Azure Blob     │
                    │  Storage        │
                    │  (Static/Media) │
                    └─────────────────┘
```

## 🔐 Security Features

### Development
- ✅ CORS configured for local origins
- ✅ Debug mode enabled
- ✅ Console email backend
- ✅ Relaxed security settings

### Production
- ✅ HTTPS enforcement
- ✅ Security headers
- ✅ Non-root containers
- ✅ Secret management
- ✅ SSL database connections
- ✅ CORS restricted to production domains

## 🚦 Health Checks

All containers include health check endpoints:
- **Backend**: `GET /health/` and `GET /ready/`
- **Frontend**: `GET /health`

## 📈 Monitoring

### Local Development
```bash
# View container stats
docker stats

# Monitor logs
docker-compose logs -f

# Check service health
curl http://localhost:8000/health/
```

### Azure Production
- Application Insights integration
- Container Apps monitoring
- Azure Monitor logs
- Custom dashboards

## 🤝 Contributing

1. **Setup local development**: `./start-local.sh`
2. **Make changes** in your feature branch
3. **Test locally**: Verify everything works
4. **Test production**: `docker-compose -f docker-compose.prod.yml up`
5. **Create PR** with deployment tested

## 📞 Support

- **Local Issues**: Check [LOCAL_DEPLOYMENT.md](LOCAL_DEPLOYMENT.md) troubleshooting
- **Azure Issues**: Check [AZURE_DEPLOYMENT.md](AZURE_DEPLOYMENT.md) troubleshooting
- **Docker Issues**: `docker system prune -a` often helps
- **Database Issues**: Reset with `docker-compose down -v`

---

**Next Steps:**
1. Choose your deployment option from the table above
2. Follow the corresponding detailed guide
3. Test your setup thoroughly before production deployment