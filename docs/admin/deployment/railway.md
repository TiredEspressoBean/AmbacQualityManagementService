# Railway Deployment Guide

This guide covers deploying and managing the application on Railway.

## Architecture

The application runs as four services on Railway:

| Service | Purpose | Config File |
|---------|---------|-------------|
| Backend | Django API + Gunicorn | `railway.toml` |
| celery-worker | Background task processing | `railway.celery.toml` |
| celery-beat | Scheduled task scheduler | `railway.celery.toml` |
| Frontend | React/Vite UI | `railway.toml` |

Plus two databases:
- **pgvector** - PostgreSQL with vector extension
- **Redis** - Message broker and cache

## Environment Variables

### Required for all backend services

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | `${{pgvector.DATABASE_URL}}` |
| `REDIS_URL` | Redis connection | `${{Redis.REDIS_URL}}` |
| `DJANGO_SECRET_KEY` | Django secret key | Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DJANGO_SETTINGS_MODULE` | Settings module | `PartsTrackerApp.settings` |

### Backend-specific

| Variable | Description |
|----------|-------------|
| `SERVICE_TYPE` | `web` (default), `worker`, or `beat` |
| `PORT` | HTTP port (set to `8000` for healthchecks) |
| `ALLOWED_HOSTS` | `.railway.app` |

### Service type configuration

The Dockerfile uses `SERVICE_TYPE` to determine what to run:
- `web` or empty: Runs Gunicorn (Django)
- `worker`: Runs Celery worker
- `beat`: Runs Celery beat scheduler

## Management Commands

### SSH into a service
```bash
railway ssh --service Backend
python manage.py createsuperuser
python manage.py shell
```

### Run command with Railway env vars locally
```bash
railway run --service Backend python manage.py migrate
railway run --service Backend python manage.py dbshell
```

### View logs
```bash
railway logs --service Backend
railway logs --service celery-worker
```

### Redeploy a service
```bash
railway redeploy --service Backend --yes
```

### Check/set variables
```bash
railway variable --service Backend
railway variable set KEY=value --service Backend
railway variable delete KEY --service Backend
```

## Healthchecks

- **Backend**: HTTP healthcheck on `/health/` endpoint
- **Celery services**: No HTTP healthcheck (background workers don't serve HTTP)

The healthcheck requires:
1. `PORT` environment variable set (e.g., `8000`)
2. Public networking enabled, OR new environment (after Oct 2025) with dual-stack networking

## Database Setup

### pgvector extension
The initial migration automatically enables pgvector:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Connecting to database
```bash
railway connect pgvector
-- or with psql directly:
psql "your-DATABASE_PUBLIC_URL"
```

## Troubleshooting

### Healthcheck fails with "service unavailable"
1. Check `PORT` is set: `railway variable --service Backend | grep PORT`
2. Ensure `ALLOWED_HOSTS` includes `.railway.app`
3. Check `SECURE_SSL_REDIRECT` is `false` (Railway handles SSL at load balancer)

### Celery can't connect to Redis
1. Check `REDIS_URL` resolves: `railway variable --service celery-worker | grep REDIS`
2. Ensure it shows actual connection string, not `${{...}}` template

### Database connection refused
1. Verify `DATABASE_URL` is set correctly
2. Check pgvector service is running
3. Use private networking URL (`.railway.internal`) for service-to-service

## Config Files

### railway.toml (Backend/Frontend)
```toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
healthcheckPath = "/health/"
healthcheckTimeout = 300
healthcheckGracePeriod = 30
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 5
```

### railway.celery.toml (Celery services)
```toml
[build]
builder = "dockerfile"
dockerfilePath = "Dockerfile"

[deploy]
# No healthcheck - celery workers don't serve HTTP
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 5
```

## Useful Links

- [Railway CLI Reference](https://docs.railway.com/reference/cli-api)
- [Railway Healthchecks](https://docs.railway.com/reference/healthchecks)
- [Railway Private Networking](https://docs.railway.com/guides/private-networking)
