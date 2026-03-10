# Azure Deployment Troubleshooting Notes

## Issues Encountered and Solutions (2025-10-23)

### Issue 1: ModuleNotFoundError - PartsTrackerApp module not found

**Problem:**
```
ModuleNotFoundError: No module named 'PartsTrackerApp'
```

**Root Cause:**
- The `azure/webapps-deploy@v3` action with `package: .` was creating `output.tar.gz` in `/home/site/wwwroot/`
- Azure was NOT extracting the tar.gz file, leaving only the compressed archive
- The startup command couldn't find the Django modules because they weren't extracted

**Solution:**
Changed deployment method from `azure/webapps-deploy@v3` to Kudu ZipDeploy API:

```yaml
- name: 'Deploy to Backend (Django Web) using ZipDeploy'
  run: |
    CREDS=$(az webapp deployment list-publishing-credentials --resource-group PartsTracker --name Parts-tracker-django --query "{username:publishingUserName, password:publishingPassword}" -o json)
    USERNAME=$(echo $CREDS | jq -r '.username')
    PASSWORD=$(echo $CREDS | jq -r '.password')

    curl -X POST \
      -u "$USERNAME:$PASSWORD" \
      --data-binary @deploy.zip \
      -H "Content-Type: application/zip" \
      https://parts-tracker-django-gqfygdhsejamauh3.scm.centralus-01.azurewebsites.net/api/zipdeploy
```

**Why this works:**
- Kudu `/api/zipdeploy` endpoint extracts files to `/home/site/wwwroot/`
- Triggers Oryx build system (respects `SCM_DO_BUILD_DURING_DEPLOYMENT=1`)
- Files are properly extracted and built

---

### Issue 2: Startup Command Reset After Deployment

**Problem:**
- Bicep template (azure/main.bicep) sets startup command correctly
- GitHub Actions deployment was overwriting the startup command

**Solution:**
Added explicit startup command preservation step after deployment:

```yaml
- name: 'Ensure startup command is preserved'
  run: |
    az webapp config set \
      --resource-group PartsTracker \
      --name Parts-tracker-django \
      --startup-file "gunicorn --bind=0.0.0.0 --timeout 600 PartsTrackerApp.wsgi"

    az webapp restart --resource-group PartsTracker --name Parts-tracker-django
```

**Key Configuration in Bicep:**
```bicep
resource backendAppConfig 'Microsoft.Web/sites/config@2023-01-01' = {
  parent: backendApp
  name: 'web'
  properties: {
    appCommandLine: 'gunicorn --bind=0.0.0.0 --timeout 600 PartsTrackerApp.wsgi'
  }
}
```

---

### Issue 3: Migration Squashing and Database Schema Mismatch

**Problem:**
```
django.db.utils.ProgrammingError: column Tracker_externalapiorderidentifier.include_in_progress does not exist
```

**Root Cause:**
- Had 13 separate migration files (0001-0013)
- Squashed all migrations into a single `0001_initial.py`
- Deployed new squashed migration
- Database still had old migration state
- Django thought migrations were applied, but schema was outdated

**Solution:**
1. Used `django-extensions` to reset database:
   ```bash
   pip install django-extensions
   # Add to INSTALLED_APPS
   python manage.py reset_db --noinput
   ```

2. Recreated pgvector extension (lost during reset):
   ```bash
   python -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('CREATE EXTENSION IF NOT EXISTS vector;'); print('Vector extension enabled')"
   ```

3. Applied fresh migrations:
   ```bash
   python manage.py migrate
   ```

**Important Notes:**
- Migration squashing requires database reset when database already has data
- pgvector extension must be recreated after `reset_db`
- Alternative: Don't squash migrations if database has existing state

---

### Issue 4: pgvector Extension Lost After Database Reset

**Problem:**
- `reset_db` command drops ALL database objects including extensions
- Migrations require pgvector extension to exist before running
- Can't use `python manage.py dbshell` in Azure App Service (psql not installed)

**Solution:**
Use Django's database connection to run raw SQL:

```bash
python -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('CREATE EXTENSION IF NOT EXISTS vector;'); print('Vector extension enabled')"
```

**Alternative Methods (for future reference):**
1. From local machine with Azure CLI:
   ```bash
   az postgres flexible-server execute \
     --name parts-tracker-django-server \
     --admin-user kdezfhzdbd \
     --admin-password "PASSWORD" \
     --database-name parts-tracker-django-database \
     --querytext "CREATE EXTENSION IF NOT EXISTS vector;"
   ```
   (Note: Requires `rdbms-connect` extension which may fail to install)

2. Enable at server level (already done in bicep):
   ```bash
   az postgres flexible-server parameter set \
     --resource-group PartsTracker \
     --server-name parts-tracker-django-server \
     --name azure.extensions \
     --value VECTOR
   ```

---

## Key Takeaways

1. **Always use Kudu ZipDeploy API for Python apps** - Don't use `azure/webapps-deploy@v3` with `package: .`
2. **Explicitly preserve startup commands** after deployment in GitHub Actions
3. **Migration squashing requires database reset** - Not recommended for production with existing data
4. **pgvector must be recreated** after database resets
5. **Azure App Service doesn't have psql** - Use Django's connection.cursor() for raw SQL

---

## Working Deployment Configuration

### GitHub Actions Workflow
- Uses Kudu ZipDeploy API for file extraction
- Explicitly sets startup command after deployment
- Restarts app to apply configuration

### Azure App Settings (from Bicep)
- `SCM_DO_BUILD_DURING_DEPLOYMENT: '1'` - Triggers Oryx build
- `appCommandLine: 'gunicorn --bind=0.0.0.0 --timeout 600 PartsTrackerApp.wsgi'` - Startup command

### Migration Strategy
- Keep migrations in version control
- Squash only when safe to reset database
- Always backup before major schema changes
- Document pgvector dependency

---

## Quick Reference Commands

### Check deployment structure in SSH:
```bash
cd /home/site/wwwroot && ls -la
```

### Enable pgvector extension in SSH:
```bash
python -c "from django.db import connection; cursor = connection.cursor(); cursor.execute('CREATE EXTENSION IF NOT EXISTS vector;'); print('Vector extension enabled')"
```

### Get PostgreSQL password from Azure:
```bash
az webapp config appsettings list --resource-group PartsTracker --name Parts-tracker-django --query "[?name=='POSTGRES_PASSWORD'].value" -o tsv
```

### Check startup command:
```bash
az webapp config show --resource-group PartsTracker --name Parts-tracker-django --query "appCommandLine"
```

### Reset database (if needed):
```bash
python manage.py reset_db --noinput
```
