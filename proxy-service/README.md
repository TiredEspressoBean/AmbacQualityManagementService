# Railway Edge Proxy

This service routes all incoming traffic to the appropriate internal service based on URL path.

## Architecture

```
Internet → proxy (public) → Backend.railway.internal:8000
                          → Frontend.railway.internal:8080
                          → docs.railway.internal:80
```

## Routing

| Path | Destination |
|------|-------------|
| `/api/*` | Backend:8000 |
| `/auth/*` | Backend:8000 |
| `/accounts/*` | Backend:8000 |
| `/admin/*` | Backend:8000 |
| `/media/*` | Backend:8000 |
| `/static/*` | Backend:8000 |
| `/docs/*` | docs:80 |
| `/*` | Frontend:8080 |

## Railway Setup

Your project already has these services:
- `Backend` - Django API (port 8000)
- `Frontend` - React SPA (port 8080)
- `docs` - MkDocs (port 80)
- `Redis`, `pgvector`, `celery-worker`, `celery-beat` - internal

To add the proxy:

1. **Add new service** `proxy` from `proxy-service/` directory

2. **Move custom domain** `uqmes.com` from Frontend to proxy

3. **Remove public domains** from Backend, Frontend, docs
   - They'll only be accessible via proxy's internal routing

4. **Update Frontend env** (if needed):
   - `VITE_API_TARGET` can be removed since proxy handles routing

## Environment Variables

The proxy uses Railway's `PORT` environment variable automatically.

No additional configuration required.
