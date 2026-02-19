# Azure Deployment for AmbacTracker

This directory contains Azure deployment configuration using Bicep templates.

## What Gets Deployed

- ✅ **Azure Cache for Redis** - For Celery message broker
- ✅ **Storage Account** - For media and static files
- ✅ **Celery Worker App Service** - Processes async tasks
- ✅ **Celery Beat App Service** - Scheduled task runner
- ✅ **Static Web App** - Frontend React application

**Reuses existing resources:**
- PostgreSQL server (parts-tracker-django-server)
- Backend App Service (Parts-tracker-django)
- App Service Plan (ASP-PartsTracker-8077)

## Prerequisites

1. Azure CLI installed and logged in:
   ```bash
   az login
   ```

2. Copy and edit the parameters file:
   ```bash
   copy azure\parameters-complete.json azure\parameters.json
   ```

3. Edit `azure/parameters.json` and fill in your actual values:
   - `djangoSecretKey` - Generate a new secret for production (currently has placeholder)
   - Optional: HubSpot, LangSmith, Microsoft auth keys (currently empty strings)
   - Optional: Email password (currently empty)

   All other values are pre-filled from your existing Azure resources.

## Deploy Infrastructure

**Single command deployment:**

```bash
# Option 1: Using parameters file (recommended)
az deployment group create \
  --resource-group PartsTracker \
  --template-file azure/main.bicep \
  --parameters azure/parameters.json

# Option 2: Use complete parameters directly (if you don't need to change anything)
az deployment group create \
  --resource-group PartsTracker \
  --template-file azure/main.bicep \
  --parameters azure/parameters-complete.json
```

This takes ~10-15 minutes (Redis provisioning is the longest part).

## What This Deployment Does

The Bicep template will:
- ✅ Create Redis cache for Celery
- ✅ Create Storage Account for media files
- ✅ Create Celery Worker App Service (separate container)
- ✅ Create Celery Beat App Service (separate container)
- ✅ Create Static Web App for frontend
- ✅ Enable pgvector on PostgreSQL
- ✅ **Update your existing backend with Redis/Storage configuration**

**Architecture:** 3 separate App Services (Django + Celery Worker + Celery Beat) sharing one App Service Plan (B2) - matching your docker-compose setup!

## After Deployment

### 1. Enable pgvector Extension in Database

The Bicep enables pgvector at the server level, but you need to create the extension in the database:

**Option A: Run the helper script (Windows)**
```powershell
.\azure\setup-pgvector.ps1
```

**Option B: Run the helper script (Linux/Mac)**
```bash
bash azure/setup-pgvector.sh
```

**Option C: Manual SQL**
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 2. Deploy Your Django Code to All Three Apps

All three apps use the **same PartsTracker Django code**, but run different commands (just like your docker-compose):

```bash
cd PartsTracker

# Deploy the same Django code to all 3 apps
az webapp up --name Parts-tracker-django --resource-group PartsTracker
az webapp up --name ambactracker-celery-worker --resource-group PartsTracker
az webapp up --name ambactracker-celery-beat --resource-group PartsTracker
```

**What each app runs (configured in Bicep):**
- **Parts-tracker-django**: Django web server (handles HTTP requests)
- **ambactracker-celery-worker**: `celery -A PartsTrackerApp worker` (processes background tasks)
- **ambactracker-celery-beat**: `celery -A PartsTrackerApp beat` (schedules periodic tasks)

Same code, different entry points! ✨

### 3. Deploy Frontend (Optional)

The Static Web App is created but needs code deployed via GitHub Actions or Static Web App CLI.
See the Azure portal for deployment token and instructions.

## Verify Deployment

Check all services are running:

```bash
# Check Celery worker
az webapp browse --name ambactracker-celery-worker --resource-group PartsTracker

# Check Celery beat
az webapp browse --name ambactracker-celery-beat --resource-group PartsTracker

# Check logs
az webapp log tail --name ambactracker-celery-worker --resource-group PartsTracker
```

## Cost Estimate

Monthly costs:
- Redis (Basic C0): ~$16/mo
- Storage Account: ~$5/mo
- App Service Plan (B2, existing): ~$62/mo (no additional cost, reused)
- Static Web Apps (Free): $0
- **Total new costs: ~$21/mo**

## Troubleshooting

### Validation fails with quota error
The template has been updated to reuse your existing App Service Plan to avoid quota issues.

### Redis connection fails
Make sure you're using the `rediss://` (with two 's') protocol for SSL connection.

### Celery tasks not running
Check that the Celery worker and beat apps have the correct `CELERY_BROKER_URL` environment variable set.

## Clean Up (Optional)

To remove only the new resources (keeping backend and database):

```bash
az redis delete --name ambactracker-redis --resource-group PartsTracker
az storage account delete --name ambactrackerstorageprod --resource-group PartsTracker
az webapp delete --name ambactracker-celery-worker --resource-group PartsTracker
az webapp delete --name ambactracker-celery-beat --resource-group PartsTracker
az staticwebapp delete --name ambactracker-frontend --resource-group PartsTracker
```
