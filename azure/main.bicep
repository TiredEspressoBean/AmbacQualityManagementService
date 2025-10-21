// Main Bicep template for AmbacTracker deployment
// Deploy with: az deployment group create --resource-group PartsTracker --template-file azure/main.bicep --parameters azure/parameters.json

param location string = 'centralus'
param projectName string = 'ambactracker'
param environment string = 'prod'

// Existing resources (we'll reference these)
param existingPostgresServer string = 'parts-tracker-django-server'
param existingBackendApp string = 'Parts-tracker-django'
param existingAppServicePlan string = 'ASP-PartsTracker-8077'

// Redis configuration
param redisName string = '${projectName}-redis'
param redisSku string = 'Basic'

// Celery App Services
param celeryWorkerAppName string = '${projectName}-celery-worker'
param celeryBeatAppName string = '${projectName}-celery-beat'

// Storage for media files
param storageAccountName string = '${projectName}storage${environment}'

// Static Web App for frontend
param frontendAppName string = '${projectName}-frontend'

// Database configuration
param postgresDatabase string = 'parts-tracker-django-database'
param postgresUser string = 'kdezfhzdbd'

// Secrets (passed at deployment time)
@secure()
param postgresPassword string

@secure()
param djangoSecretKey string

@secure()
param hubspotApiKey string = ''

@secure()
param langsmithApiKey string = ''

@secure()
param microsoftClientId string = ''

@secure()
param microsoftClientSecret string = ''

@secure()
param emailHostPassword string = ''

// Django configuration
param djangoDebug string = 'False'
param djangoSuperuserUsername string = 'admin'
param djangoSuperuserEmail string = 'admin@email.com'
@secure()
param djangoSuperuserPassword string

// Email configuration
param emailHost string = 'outbound-us1.ppe-hosted.com'
param emailHostUser string = 'sales@ambacinternational.com'
param emailBackend string = 'django.core.mail.backends.smtp.EmailBackend'

// Frontend/CORS configuration - These will be computed after deployment
// Leave empty or provide custom domains if you have them
param customFrontendDomain string = ''
param customBackendDomain string = ''

// ============================================
// Enable pgvector on existing PostgreSQL server
// ============================================
resource postgresServerResource 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' existing = {
  name: existingPostgresServer
}

resource pgvectorConfig 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2023-03-01-preview' = {
  parent: postgresServerResource
  name: 'azure.extensions'
  properties: {
    value: 'VECTOR'
    source: 'user-override'
  }
}

// ============================================
// Azure Cache for Redis
// ============================================
resource redis 'Microsoft.Cache/redis@2023-08-01' = {
  name: redisName
  location: location
  properties: {
    sku: {
      name: redisSku
      family: 'C'
      capacity: 0
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    redisConfiguration: {
      'maxmemory-policy': 'allkeys-lru'
    }
  }
}

// ============================================
// Storage Account for media files
// ============================================
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: true
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

resource mediaContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'media'
  properties: {
    publicAccess: 'Blob'
  }
}

resource staticContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'static'
  properties: {
    publicAccess: 'Blob'
  }
}

// ============================================
// Reference existing App Service Plan (all 3 apps share this)
// ============================================
resource existingAppServicePlanResource 'Microsoft.Web/serverfarms@2023-01-01' existing = {
  name: existingAppServicePlan
}

// ============================================
// Update Existing Backend App with Redis and Storage
// ============================================
resource backendApp 'Microsoft.Web/sites@2023-01-01' existing = {
  name: existingBackendApp
}

resource backendAppConfig 'Microsoft.Web/sites/config@2023-01-01' = {
  parent: backendApp
  name: 'web'
  properties: {
    appCommandLine: 'gunicorn --bind=0.0.0.0 --timeout 600 --chdir /home/site/wwwroot PartsTrackerApp.wsgi'
  }
}

resource backendAppSettings 'Microsoft.Web/sites/config@2023-01-01' = {
  parent: backendApp
  name: 'appsettings'
  dependsOn: [backendAppConfig]
  properties: {
    WEBSITES_PORT: '8000'
    SCM_DO_BUILD_DURING_DEPLOYMENT: '1'
    DJANGO_SETTINGS_MODULE: 'PartsTrackerApp.settings_azure'
    DJANGO_SECRET_KEY: djangoSecretKey
    DJANGO_DEBUG: djangoDebug
    DJANGO_SUPERUSER_USERNAME: djangoSuperuserUsername
    DJANGO_SUPERUSER_EMAIL: djangoSuperuserEmail
    DJANGO_SUPERUSER_PASSWORD: djangoSuperuserPassword
    POSTGRES_HOST: '${existingPostgresServer}.postgres.database.azure.com'
    POSTGRES_DB: postgresDatabase
    POSTGRES_USER: postgresUser
    POSTGRES_PASSWORD: postgresPassword
    POSTGRES_PORT: '5432'
    REDIS_URL: 'rediss://:${redis.listKeys().primaryKey}@${redis.properties.hostName}:6380/0'
    CELERY_BROKER_URL: 'rediss://:${redis.listKeys().primaryKey}@${redis.properties.hostName}:6380/0'
    REDIS_HOST: redis.properties.hostName
    AZURE_STORAGE_ACCOUNT_NAME: storageAccount.name
    AZURE_STORAGE_ACCOUNT_KEY: storageAccount.listKeys().keys[0].value
    AZURE_STORAGE_CONTAINER_NAME_MEDIA: 'media'
    AZURE_STORAGE_CONTAINER_NAME_STATIC: 'static'
    HUBSPOT_API_KEY: hubspotApiKey
    LANGSMITH_API_KEY: langsmithApiKey
    MICROSOFT_CLIENT_ID: microsoftClientId
    MICROSOFT_CLIENT_SECRET: microsoftClientSecret
    EMAIL_HOST: emailHost
    EMAIL_HOST_USER: emailHostUser
    EMAIL_HOST_PASSWORD: emailHostPassword
    EMAIL_BACKEND: emailBackend
    ALLOWED_HOSTS: '${backendApp.properties.defaultHostName}'
    CORS_ALLOWED_ORIGINS: empty(customFrontendDomain) ? 'https://${staticWebApp.properties.defaultHostname}' : 'https://${customFrontendDomain}'
    CSRF_TRUSTED_ORIGINS: 'https://${backendApp.properties.defaultHostName}'
    FRONTEND_URL: empty(customFrontendDomain) ? 'https://${staticWebApp.properties.defaultHostname}' : 'https://${customFrontendDomain}'
  }
}

// ============================================
// Celery Worker App Service
// ============================================
resource celeryWorkerApp 'Microsoft.Web/sites@2023-01-01' = {
  name: celeryWorkerAppName
  location: location
  kind: 'app,linux'
  properties: {
    serverFarmId: existingAppServicePlanResource.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.12'
      alwaysOn: true
      appCommandLine: 'celery -A PartsTrackerApp.celery_app worker --loglevel=info'
      appSettings: [
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: '1'
        }
        {
          name: 'DJANGO_SETTINGS_MODULE'
          value: 'PartsTrackerApp.settings_azure'
        }
        {
          name: 'DJANGO_SECRET_KEY'
          value: djangoSecretKey
        }
        {
          name: 'POSTGRES_HOST'
          value: '${existingPostgresServer}.postgres.database.azure.com'
        }
        {
          name: 'POSTGRES_DB'
          value: postgresDatabase
        }
        {
          name: 'POSTGRES_USER'
          value: postgresUser
        }
        {
          name: 'POSTGRES_PASSWORD'
          value: postgresPassword
        }
        {
          name: 'POSTGRES_PORT'
          value: '5432'
        }
        {
          name: 'REDIS_URL'
          value: 'rediss://:${redis.listKeys().primaryKey}@${redis.properties.hostName}:6380/0'
        }
        {
          name: 'CELERY_BROKER_URL'
          value: 'rediss://:${redis.listKeys().primaryKey}@${redis.properties.hostName}:6380/0'
        }
        {
          name: 'REDIS_HOST'
          value: redis.properties.hostName
        }
        {
          name: 'AZURE_STORAGE_ACCOUNT_NAME'
          value: storageAccount.name
        }
        {
          name: 'AZURE_STORAGE_ACCOUNT_KEY'
          value: storageAccount.listKeys().keys[0].value
        }
        {
          name: 'AZURE_STORAGE_CONTAINER_NAME_MEDIA'
          value: 'media'
        }
        {
          name: 'AZURE_STORAGE_CONTAINER_NAME_STATIC'
          value: 'static'
        }
        {
          name: 'HUBSPOT_API_KEY'
          value: hubspotApiKey
        }
        {
          name: 'LANGSMITH_API_KEY'
          value: langsmithApiKey
        }
      ]
    }
  }
}

// ============================================
// Celery Beat App Service
// ============================================
resource celeryBeatApp 'Microsoft.Web/sites@2023-01-01' = {
  name: celeryBeatAppName
  location: location
  kind: 'app,linux'
  properties: {
    serverFarmId: existingAppServicePlanResource.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.12'
      alwaysOn: true
      appCommandLine: 'celery -A PartsTrackerApp.celery_app beat --loglevel=info'
      appSettings: [
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: '1'
        }
        {
          name: 'DJANGO_SETTINGS_MODULE'
          value: 'PartsTrackerApp.settings_azure'
        }
        {
          name: 'DJANGO_SECRET_KEY'
          value: djangoSecretKey
        }
        {
          name: 'POSTGRES_HOST'
          value: '${existingPostgresServer}.postgres.database.azure.com'
        }
        {
          name: 'POSTGRES_DB'
          value: postgresDatabase
        }
        {
          name: 'POSTGRES_USER'
          value: postgresUser
        }
        {
          name: 'POSTGRES_PASSWORD'
          value: postgresPassword
        }
        {
          name: 'POSTGRES_PORT'
          value: '5432'
        }
        {
          name: 'REDIS_URL'
          value: 'rediss://:${redis.listKeys().primaryKey}@${redis.properties.hostName}:6380/0'
        }
        {
          name: 'CELERY_BROKER_URL'
          value: 'rediss://:${redis.listKeys().primaryKey}@${redis.properties.hostName}:6380/0'
        }
        {
          name: 'REDIS_HOST'
          value: redis.properties.hostName
        }
        {
          name: 'AZURE_STORAGE_ACCOUNT_NAME'
          value: storageAccount.name
        }
        {
          name: 'AZURE_STORAGE_ACCOUNT_KEY'
          value: storageAccount.listKeys().keys[0].value
        }
        {
          name: 'AZURE_STORAGE_CONTAINER_NAME_MEDIA'
          value: 'media'
        }
        {
          name: 'AZURE_STORAGE_CONTAINER_NAME_STATIC'
          value: 'static'
        }
        {
          name: 'HUBSPOT_API_KEY'
          value: hubspotApiKey
        }
        {
          name: 'LANGSMITH_API_KEY'
          value: langsmithApiKey
        }
      ]
    }
  }
}

// ============================================
// Static Web App for frontend
// ============================================
resource staticWebApp 'Microsoft.Web/staticSites@2023-01-01' = {
  name: frontendAppName
  location: 'eastus2'  // Static Web Apps not available in eastus, using eastus2
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {
    buildProperties: {
      appLocation: '/ambac-tracker-ui'
      outputLocation: 'dist'
    }
  }
}

// ============================================
// Outputs
// ============================================
output redisHostName string = redis.properties.hostName
output storageAccountName string = storageAccount.name
output backendUrl string = backendApp.properties.defaultHostName
output celeryWorkerUrl string = celeryWorkerApp.properties.defaultHostName
output celeryBeatUrl string = celeryBeatApp.properties.defaultHostName
output frontendUrl string = staticWebApp.properties.defaultHostname
