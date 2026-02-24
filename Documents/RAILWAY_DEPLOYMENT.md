# Railway Deployment - Technical Reference

Internal reference for deployment configuration and troubleshooting.

## Project Details

- **Project Name**: enthusiastic-reverence
- **Environment**: production
- **Repository**: TiredEspressoBean/AmbacQualityManagementService

## Services

| Service | Config File | SERVICE_TYPE | Healthcheck |
|---------|-------------|--------------|-------------|
| Backend | `railway.toml` | `web` (default) | `/health/` |
| celery-worker | `railway.celery.toml` | `worker` | None |
| celery-beat | `railway.celery.toml` | `beat` | None |
| Frontend | `ambac-tracker-ui/` | N/A | `/` |
| pgvector | Railway template | N/A | N/A |
| Redis | Railway service | N/A | N/A |

## Key Configuration Decisions

### Single Dockerfile, Multiple Services
The backend Dockerfile uses `SERVICE_TYPE` env var to determine what to run:
```dockerfile
CMD if [ "$SERVICE_TYPE" = "worker" ]; then \
      celery -A PartsTrackerApp worker -l info; \
    elif [ "$SERVICE_TYPE" = "beat" ]; then \
      celery -A PartsTrackerApp beat -l info; \
    else \
      python manage.py migrate --noinput && \
      python manage.py collectstatic --noinput && \
      gunicorn PartsTrackerApp.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4; \
    fi
```

### Separate Config Files
- `railway.toml` - For services needing HTTP healthchecks (Backend, Frontend)
- `railway.celery.toml` - For background workers (no healthcheck)

Config-as-code locks UI fields, so separate files allow per-service customization.

### Database Choice: pgvector Template
Railway's base Postgres does NOT include pgvector binaries. Must use:
- pgvector-pg17 template: https://railway.com/deploy/qcuy_M
- Extension enabled via migration in `0001_initial.py`

`railway connect` doesn't work with pgvector template (Docker-based, not managed).

## Environment Variable Patterns

### Working References
```
DATABASE_URL = ${{pgvector.DATABASE_URL}}
REDIS_URL = ${{Redis.REDIS_URL}}
```

### Broken Patterns (Don't Use)
```
# These don't resolve properly:
CELERY_BROKER_URL = redis://default:${{Redis.REDISPASSWORD}}@${{Redis.RAILWAY_PRIVATE_DOMAIN}}:6379/0
# Results in: redis://default:@:6379/0 (empty password/host)
```

### Shared Variables
Shared variables (`${{shared.X}}`) have resolution issues. Set variables directly on each service instead.

## Healthcheck Requirements

For healthchecks to work:
1. **PORT must be set explicitly** - Railway needs to know which port to hit internally
2. **ALLOWED_HOSTS** must include `.railway.app` and `healthcheck.railway.app`
3. **SECURE_SSL_REDIRECT = false** - Railway's healthcheck uses HTTP, not HTTPS
4. **Public networking OR new environment** - Legacy environments (pre-Oct 2025) are IPv6-only; healthchecks use IPv4

### Why Public Domain Fixed Healthchecks
When you generate a public domain, Railway's HTTP proxy auto-detects your port and configures routing. The healthcheck piggybacks on that configuration. Setting `PORT` explicitly achieves the same without public domain.

## Celery Workers Don't Need HTTP Healthchecks

Celery workers:
- Don't serve HTTP requests
- Auto-reconnect to Redis on failure
- Are restarted by Railway's `restartPolicyType = "on_failure"`

The `celery-healthcheck` package exists but adds complexity. Standard approach is no HTTP healthcheck for background workers.

## CLI Commands Reference

```bash
# Link to project
railway link

# Check status
railway status

# View/set variables
railway variable --service Backend
railway variable set PORT=8000 --service Backend
railway variable delete BROKEN_VAR --service celery-worker

# Logs
railway logs --service Backend
railway logs --service celery-worker

# Redeploy
railway redeploy --service Backend --yes

# SSH into container
railway ssh --service Backend

# Run command with Railway env
railway run --service Backend python manage.py createsuperuser

# Connect to database (only works with managed Postgres, not pgvector template)
railway connect Postgres
```

## Troubleshooting Log

### Issue: Healthcheck "service unavailable"
**Cause**: Multiple possible causes
1. SECURE_SSL_REDIRECT = true (302 redirect, not 200)
2. PORT not set (Railway doesn't know which port)
3. ALLOWED_HOSTS missing Railway domains
4. TenantMiddleware not exempting /health/ path

**Fix**:
- Set `SECURE_SSL_REDIRECT = false` (Railway handles SSL)
- Set `PORT = 8000` explicitly
- Add `/health/` to TenantMiddleware.TENANT_EXEMPT_PATHS

### Issue: Celery can't connect to Redis
**Cause**: Manually constructed CELERY_BROKER_URL with unresolved variables
**Fix**: Delete CELERY_BROKER_URL, let Django fall back to REDIS_URL

### Issue: "type vector does not exist"
**Cause**: pgvector extension not enabled
**Fix**:
1. Use pgvector template (not base Postgres)
2. Run `CREATE EXTENSION IF NOT EXISTS vector;`
3. Or add to migrations (already in 0001_initial.py)

### Issue: railway connect "No supported database found"
**Cause**: pgvector template is Docker-based, not Railway managed DB
**Fix**: Connect directly via psql using DATABASE_PUBLIC_URL

## Files Modified for Railway

- `PartsTracker/Dockerfile` - Added SERVICE_TYPE logic
- `PartsTracker/railway.toml` - Healthcheck config for web services
- `PartsTracker/railway.celery.toml` - No healthcheck for workers
- `PartsTracker/PartsTrackerApp/settings.py`:
  - Added `dj_database_url` for DATABASE_URL parsing
  - Set `SECURE_SSL_REDIRECT = false` by default
  - Added `.railway.app` to ALLOWED_HOSTS
  - Added CORS regex for Railway domains
  - CELERY_BROKER_URL falls back to REDIS_URL
- `PartsTracker/Tracker/middleware.py` - Added `/health/` to exempt paths
- `PartsTracker/Tracker/migrations/0001_initial.py` - Added pgvector extension

## Costs

Railway pricing:
- **Hobby**: $5/mo + usage over $5
- **Pro**: $20/mo + usage over $20

Estimated for this setup: $10-30/month depending on usage.

## Future Considerations

1. **Custom Domain**: Add custom domain for production (removes .railway.app dependency)
2. **Redis Persistence**: Consider Redis with persistence for production
3. **Scaling**: Celery workers can be scaled horizontally
4. **Monitoring**: Add proper monitoring/alerting beyond Railway's basic metrics
