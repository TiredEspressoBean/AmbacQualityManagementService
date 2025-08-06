# Azure Container Apps Deployment Guide

This guide provides step-by-step instructions for deploying your Django + React + PostgreSQL application to Azure Container Apps.

## Prerequisites

1. **Azure CLI** installed and configured
   ```bash
   az --version
   az login
   
   # Install Container Apps extension
   az extension add --name containerapp --upgrade
   ```

2. **Docker** installed and running
   ```bash
   docker --version
   ```

3. **Azure subscription** with appropriate permissions

## Step 1: Create Azure Resources

### 1.1 Set Environment Variables
```bash
# Set your preferred values
export RESOURCE_GROUP="parts-tracker-rg"
export LOCATION="eastus"
export ACR_NAME="partstrackeracr"  # Must be globally unique
export POSTGRES_SERVER="parts-tracker-postgres"  # Must be globally unique
export POSTGRES_PASSWORD="YourStrongPassword123!"
export CONTAINER_ENV="parts-tracker-env"
```

### 1.2 Create Resource Group
```bash
az group create --name $RESOURCE_GROUP --location $LOCATION
```

### 1.3 Create Azure Container Registry (ACR)
```bash
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic --admin-enabled true

# Get ACR credentials
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username --output tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value --output tsv)
```

### 1.4 Create PostgreSQL Flexible Server
```bash
az postgres flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name $POSTGRES_SERVER \
  --location $LOCATION \
  --admin-user parts_tracker_user \
  --admin-password $POSTGRES_PASSWORD \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 16 \
  --storage-size 32 \
  --public-access 0.0.0.0

# Create database
az postgres flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $POSTGRES_SERVER \
  --database-name parts_tracker

# Configure firewall for Azure services
az postgres flexible-server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --name $POSTGRES_SERVER \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

### 1.5 Create Container Apps Environment
```bash
az containerapp env create \
  --name $CONTAINER_ENV \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION
```

## Step 2: Prepare Application for Production

### 2.1 Update Requirements (Optional for Azure Storage)
If you want to use Azure Blob Storage for static/media files, add to your requirements.txt:
```bash
# Add to PartsTracker/requirements.txt
echo "django-storages[azure]==1.14.4" >> PartsTracker/requirements.txt
```

## Step 3: Build and Push Docker Images

### 3.1 Build Backend Image
```bash
# Log in to ACR
az acr login --name $ACR_NAME

# Build and push backend
cd PartsTracker
docker build -f Dockerfile.prod -t $ACR_NAME.azurecr.io/parts-tracker-backend:latest .
docker push $ACR_NAME.azurecr.io/parts-tracker-backend:latest
cd ..
```

### 3.2 Build Frontend Image
```bash
# Build and push frontend
cd ../ambac-tracker-ui
docker build -f Dockerfile.prod \
  --build-arg VITE_API_TARGET=https://parts-tracker-backend.${LOCATION}.azurecontainerapps.io \
  -t $ACR_NAME.azurecr.io/parts-tracker-frontend:latest .
docker push $ACR_NAME.azurecr.io/parts-tracker-frontend:latest
```

## Step 4: Deploy Container Apps

### 4.1 Deploy Backend Container App
```bash
az containerapp create \
  --name parts-tracker-backend \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_ENV \
  --image $ACR_NAME.azurecr.io/parts-tracker-backend:latest \
  --target-port 8000 \
  --ingress external \
  --registry-server $ACR_NAME.azurecr.io \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --secrets django-secret-key="$(openssl rand -base64 50)" \
    postgres-password="$POSTGRES_PASSWORD" \
    acr-password="$ACR_PASSWORD" \
  --env-vars \
    DJANGO_SECRET_KEY=secretref:django-secret-key \
    DJANGO_DEBUG=False \
    DJANGO_SETTINGS_MODULE=PartsTrackerApp.settings_azure \
    POSTGRES_DB=parts_tracker \
    POSTGRES_USER=parts_tracker_user \
    POSTGRES_PASSWORD=secretref:postgres-password \
    POSTGRES_HOST=$POSTGRES_SERVER.postgres.database.azure.com \
    POSTGRES_PORT=5432 \
    ALLOWED_HOSTS="parts-tracker-backend.${LOCATION}.azurecontainerapps.io,localhost,127.0.0.1" \
    CORS_ALLOWED_ORIGINS="https://parts-tracker-frontend.${LOCATION}.azurecontainerapps.io" \
  --cpu 1.0 \
  --memory 2Gi \
  --min-replicas 1 \
  --max-replicas 5
```

### 4.2 Deploy Frontend Container App
```bash
# Get backend FQDN
BACKEND_FQDN=$(az containerapp show --name parts-tracker-backend --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn --output tsv)

az containerapp create \
  --name parts-tracker-frontend \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_ENV \
  --image $ACR_NAME.azurecr.io/parts-tracker-frontend:latest \
  --target-port 80 \
  --ingress external \
  --registry-server $ACR_NAME.azurecr.io \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --secrets acr-password="$ACR_PASSWORD" \
  --env-vars \
    VITE_API_TARGET="https://$BACKEND_FQDN" \
  --cpu 0.5 \
  --memory 1Gi \
  --min-replicas 1 \
  --max-replicas 3
```

### 4.3 Update Backend CORS Settings
```bash
# Get frontend FQDN
FRONTEND_FQDN=$(az containerapp show --name parts-tracker-frontend --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn --output tsv)

# Update backend with correct CORS origins
az containerapp update \
  --name parts-tracker-backend \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars \
    CORS_ALLOWED_ORIGINS="https://$FRONTEND_FQDN"
```

## Step 5: Configure Custom Domain (Optional)

### 5.1 Add Custom Domain to Container Apps
```bash
# For backend
az containerapp hostname add \
  --name parts-tracker-backend \
  --resource-group $RESOURCE_GROUP \
  --hostname api.yourdomain.com

# For frontend
az containerapp hostname add \
  --name parts-tracker-frontend \
  --resource-group $RESOURCE_GROUP \
  --hostname app.yourdomain.com
```

### 5.2 Configure SSL Certificates
```bash
# Container Apps automatically provision managed certificates for custom domains
# Update your DNS records to point to the Container Apps FQDNs
```

## Step 6: Database Migration and Setup

### 6.1 Run Initial Migrations
```bash
# Connect to the backend container and run migrations
az containerapp exec \
  --name parts-tracker-backend \
  --resource-group $RESOURCE_GROUP \
  --command "python manage.py migrate"

# Create superuser (optional)
az containerapp exec \
  --name parts-tracker-backend \
  --resource-group $RESOURCE_GROUP \
  --command "python manage.py createsuperuser"
```

## Step 7: Monitoring and Logging

### 7.1 Enable Application Insights (Optional)
```bash
# Create Application Insights instance
az monitor app-insights component create \
  --app parts-tracker-insights \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP

# Get instrumentation key
INSIGHTS_KEY=$(az monitor app-insights component show \
  --app parts-tracker-insights \
  --resource-group $RESOURCE_GROUP \
  --query instrumentationKey \
  --output tsv)

# Update backend container app with Application Insights
az containerapp update \
  --name parts-tracker-backend \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars APPINSIGHTS_INSTRUMENTATIONKEY="$INSIGHTS_KEY"
```

### 7.2 View Logs
```bash
# Backend logs
az containerapp logs show \
  --name parts-tracker-backend \
  --resource-group $RESOURCE_GROUP \
  --follow

# Frontend logs
az containerapp logs show \
  --name parts-tracker-frontend \
  --resource-group $RESOURCE_GROUP \
  --follow
```

## Step 8: Production Checklist

### 8.1 Security Configuration
- [ ] Set strong `DJANGO_SECRET_KEY`
- [ ] Configure proper `ALLOWED_HOSTS`
- [ ] Set `DJANGO_DEBUG=False`
- [ ] Configure HTTPS redirect
- [ ] Set up proper CORS origins
- [ ] Enable PostgreSQL SSL

### 8.2 Performance Optimization
- [ ] Configure container resources (CPU/Memory)
- [ ] Set up auto-scaling rules
- [ ] Enable compression in nginx
- [ ] Configure static file caching
- [ ] Set up CDN for static assets (optional)

### 8.3 Backup and Recovery
- [ ] Configure PostgreSQL automated backups
- [ ] Set up database point-in-time recovery
- [ ] Create deployment automation scripts
- [ ] Document rollback procedures

## Step 9: Continuous Deployment (Optional)

### 9.1 GitHub Actions Setup
Create `.github/workflows/azure-deploy.yml`:

```yaml
name: Deploy to Azure Container Apps

on:
  push:
    branches: [ main ]

env:
  AZURE_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
  AZURE_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
  AZURE_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Log in to Azure
        uses: azure/login@v1
        with:
          client-id: ${{ env.AZURE_CLIENT_ID }}
          tenant-id: ${{ env.AZURE_TENANT_ID }}
          subscription-id: ${{ env.AZURE_SUBSCRIPTION_ID }}
      
      - name: Build and deploy
        run: |
          # Build and push images
          # Update container apps
```

## Troubleshooting

### Common Issues

1. **Container fails to start**
   - Check logs: `az containerapp logs show --name <app-name> --resource-group <rg>`
   - Verify environment variables
   - Check health endpoints: `/health/` and `/ready/`

2. **Database connection fails**
   - Verify PostgreSQL firewall rules
   - Check connection string format
   - Ensure SSL is enabled

3. **Frontend can't reach backend**
   - Verify CORS configuration
   - Check backend FQDN in frontend environment
   - Ensure ingress is enabled on backend

### Useful Commands

```bash
# Get container app URLs
az containerapp show --name parts-tracker-backend --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn
az containerapp show --name parts-tracker-frontend --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn

# Scale container apps
az containerapp update --name parts-tracker-backend --resource-group $RESOURCE_GROUP --min-replicas 2 --max-replicas 10

# Update container image
az containerapp update --name parts-tracker-backend --resource-group $RESOURCE_GROUP --image $ACR_NAME.azurecr.io/parts-tracker-backend:v2

# Delete resources (cleanup)
az group delete --name $RESOURCE_GROUP --yes --no-wait
```

## Cost Optimization

1. **Use appropriate SKUs**
   - PostgreSQL: Start with Burstable tier
   - Container Apps: Set appropriate CPU/memory limits

2. **Configure auto-scaling**
   - Set minimum replicas to 1 for development
   - Use HTTP-based scaling rules

3. **Monitor usage**
   - Use Azure Cost Management
   - Set up budget alerts

## Support

For issues and questions:
1. Check Azure Container Apps documentation
2. Review application logs
3. Verify configuration against this guide
4. Contact your Azure support team

---

**Note**: Replace placeholder values (like `yourdomain.com`, passwords, etc.) with your actual values before running commands.