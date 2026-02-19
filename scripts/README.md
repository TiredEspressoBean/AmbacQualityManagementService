# Development Scripts

## Setup (New Developers)

1. Copy `.env.example` to `.env` and set your `POSTGRES_PASSWORD`
2. Run the setup script:

Start PostgreSQL and Redis containers (reads credentials from `.env`):

```powershell
# Windows
.\scripts\setup-dev.ps1

# macOS/Linux
chmod +x scripts/setup-dev.sh && ./scripts/setup-dev.sh
```

Then run Django locally:

```bash
cd PartsTracker
python manage.py migrate
python manage.py runserver
```

Containers created:
- `partstracker-postgres` - PostgreSQL with pgvector on localhost:5432
- `partstracker-redis` - Redis on localhost:6379

## Stop/Remove Containers

```bash
docker stop partstracker-postgres partstracker-redis
docker rm partstracker-postgres partstracker-redis

# To also delete data:
docker volume rm partstracker_pgdata
```
