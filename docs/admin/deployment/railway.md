# Railway Deployment Guide

This guide covers deploying and managing the application on Railway.

## Architecture

The project is **enthusiastic-reverence**, with a single **production** environment
running **eight services**. Names below are exactly as the Railway CLI expects them
after `--service`, **case included**.

| Service | Purpose |
|---------|---------|
| `Backend` | Django API + Gunicorn |
| `Frontend` | React/Vite UI |
| `proxy-caddy` | Reverse proxy and TLS termination in front of the app |
| `celery-worker` | Background task processing |
| `celery-beat` | Scheduled task scheduler |
| `docs` | MkDocs documentation — lowercase |
| `pgvector` | PostgreSQL with the vector extension |
| `Redis` | Message broker and cache |

!!! warning "Confirm the service list before trusting any page about deployment"
    Services get added, and a page like this one goes stale quietly. Run
    `railway status` or open the project to see what is actually deployed before
    following instructions that name a service.

**Config files in the repo:** `PartsTracker/railway.toml`,
`PartsTracker/railway.celery.toml`, `docs-service/railway.toml` and
`proxy-service/railway.toml`.

The Celery services build from the **same backend image** with a different start
command — `railway.celery.toml` differs from the backend's only in dropping the
HTTP healthcheck, since a worker serves no HTTP.

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
| `SERVICE_TYPE` | `web` (default), `worker`, or `beat`. Dispatched in `PartsTracker/Dockerfile`'s `CMD` — `worker` and `beat` start Celery, anything else migrates and starts Gunicorn. If a Celery service comes up serving HTTP, this is the variable to check. |
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

### railway.toml (Backend)
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

## Documentation Service

The docs service serves MkDocs-generated documentation.

### Deploying the docs service

1. In Railway dashboard, click "New Service"
2. Select "GitHub Repo" and choose this repository
3. Set **Root Directory** to `/` (repo root)
4. Set **Config File Path** to `docs-service/railway.toml`
5. Deploy

The service builds documentation from `docs/` folder using MkDocs and serves via Caddy.

### docs-service/railway.toml
```toml
[build]
builder = "dockerfile"
dockerfilePath = "docs-service/Dockerfile"

[deploy]
healthcheckPath = "/"
healthcheckTimeout = 100
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

## Path-based routing

All services sit behind one domain, routed by **`proxy-service`** — a Caddy
reverse proxy deployed as its own Railway service. Its `Caddyfile` reads three
environment variables and routes on path:

| Variable | Points at |
|----------|-----------|
| `BACKEND_URL` | e.g. `backend.railway.internal:8000` |
| `FRONTEND_URL` | e.g. `frontend.railway.internal:8080` |
| `DOCS_URL` | e.g. `docs.railway.internal:80` |

| Path | Destination |
|------|-------------|
| `/api/*`, `/auth/*`, `/accounts/*`, `/admin/*`, `/media/*` | Backend |
| `/docs/*` | Docs service |
| Everything else | Frontend |

Routing is over Railway **private networking**, so the backend and frontend do
not need public domains of their own — only the proxy does.

## Useful Links

- [Railway CLI Reference](https://docs.railway.com/reference/cli-api)
- [Railway Healthchecks](https://docs.railway.com/reference/healthchecks)
- [Railway Private Networking](https://docs.railway.com/guides/private-networking)
- [Cloudflare Workers](https://developers.cloudflare.com/workers/)
