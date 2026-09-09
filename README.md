# UQMES

Quality Management System for manufacturing parts tracking. Paths and some
identifiers say "Ambac" / "AmbacTracker" -- that's the reference customer.

Two ways to run it: the Docker Compose stack (whole system, TLS, Celery, docs)
or directly on the host (faster edit loop, what day-to-day development uses).

## Quick start -- Docker Compose

1. **Create the two environment files.** They serve different purposes and both
   are gitignored:

   ```bash
   cp .env.docker.example .env.docker   # injected into the containers
   cp .env.example .env                 # read by compose for ${...} interpolation
   ```

2. **Fill in the required values.** `.env.docker` marks them `CHANGE-ME` and
   documents each one:

   - `DJANGO_SECRET_KEY`
   - `FIELD_ENCRYPTION_KEY` -- a Fernet key. Required, and permanent: rotating
     it makes every existing encrypted column unreadable.
   - `DJANGO_SUPERUSER_PASSWORD` -- your first login.

   In `.env`, set `POSTGRES_PASSWORD` and `REDIS_PASSWORD`. Compose derives both
   the database URL and the Redis URLs from these, so the app and the servers
   can't drift apart.

3. **Start the stack:**

   ```bash
   docker compose --profile local up -d --build
   ```

   > **The `--profile` is not optional.** Every application service is
   > profile-gated. A bare `docker compose up -d` starts only `postgres` and
   > `redis` -- no backend, no Caddy, no frontend -- and looks like it worked.

   First boot runs migrations, `setup_defaults`, `setup_database` (extensions,
   groups, audit triggers), creates the superuser, and builds the frontend and
   docs. Give it a few minutes; `docker compose --profile local logs -f backend`
   shows progress.

4. **Open it:** <https://localhost> -- Caddy serves the frontend and proxies
   `/api`, `/auth`, `/admin`, `/media`, `/static` to the backend. The
   certificate is self-signed, so expect a browser warning on first visit.

   - Django admin: <https://localhost/admin>
   - MkDocs: <https://localhost/docs/>
   - Postgres and Redis publish **no ports** -- reach them through
     `docker compose exec` (see Commands).

## Quick start -- host

The default development loop. Needs Postgres reachable on the host with the
`vector` extension available.

```bash
cp .env.example .env                 # then fill in the same required values

cd PartsTracker && python manage.py migrate && python manage.py setup_database
python manage.py seed_dev            # or seed_demo
python manage.py runserver           # http://localhost:8000

cd ../ambac-tracker-ui && bun install && bun run dev   # http://localhost:5173
```

The Vite dev server proxies API calls through to Django, so use the 5173 URL,
not 8000.

## Stack

| | |
|---|---|
| Backend | Django 5.1 + DRF, Celery (Redis broker), Typst for PDF reports |
| Frontend | React + Vite + TanStack Router, built with Bun |
| Database | PostgreSQL 15 (`ankane/pgvector`) with pgvector, pgaudit, pgBackRest |
| Proxy | Caddy -- TLS, static files, API routing |

Compose profiles: **`local`** (runserver, hot reload, seeded admin),
**`production`** (gunicorn, `DEBUG=False`, backup scheduler),
**`backup`** (one-shot restore and media-sync jobs).

## Environment variables

`.env.docker.example` and `.env.example` are the authoritative lists -- each
variable is documented inline. In short:

**Required:** `DJANGO_SECRET_KEY`, `FIELD_ENCRYPTION_KEY`,
`POSTGRES_PASSWORD`, `DJANGO_SUPERUSER_*`.

**Worth knowing:**

- `DJANGO_DEBUG` defaults to `False` in `.env.docker`. The three `local`-profile
  services override it to `True` in `docker-compose.yml`. Leave the default
  alone -- it's what keeps the production Celery workers from building
  `localhost` links into outbound email.
- `DEPLOYMENT_MODE` **defaults to `saas` in `settings.py` when unset**, so both
  templates set it explicitly to `dedicated`. Dedicated is one tenant with no
  tenant-selection UI, which is what a local stack or a single-customer on-prem
  install wants; `saas` turns on subdomain tenant routing and needs
  `TENANT_BASE_DOMAIN` plus wildcard DNS to be usable. `DEFAULT_TENANT_SLUG`
  only takes effect in dedicated mode.
- Email is optional. With no `EMAIL_BACKEND`, mail goes to the console;
  invitation and password-reset links are copyable from the UI at
  `/admin/users`, so onboarding works with no mail path configured.

## Commands

```bash
# Logs (profile required here too)
docker compose --profile local logs -f backend

# Shell into the backend
docker compose --profile local exec backend python manage.py shell

# psql
docker compose exec postgres psql -U postgres -d tracker_AMBAC

# Stop
docker compose --profile local down

# Rebuild after code changes
docker compose --profile local up -d --build

# Reset everything, database included
docker compose --profile local down -v && docker compose --profile local up -d --build
```

## Development commands

Run these on the host (they need the project venv, not a container).

```bash
cd PartsTracker

# Tests. Always pass --noinput: a killed run orphans its test databases and the
# next run then blocks forever on an interactive prompt.
python manage.py test --noinput
python manage.py test --parallel 4 --noinput          # full sweep, ~35% faster
python manage.py test --keepdb Tracker.tests.test_x   # narrow iteration

# If a run dies with "database test_... already exists":
python manage.py clean_test_dbs
```

A `--parallel` failure that passes when re-run serially is a parallelism flake,
not a regression -- confirm serially before chasing it.

**After changing anything in `serializers/` or `viewsets/`**, regenerate the API
contract and commit it in the same change -- the frontend's generated client is
derived from it:

```bash
cd PartsTracker      && python manage.py spectacular --file schema.yaml --fail-on-warn
cd ../ambac-tracker-ui && bun run generate-api && bun run typecheck
```

`--fail-on-warn` matters: it turns schema drift into a hard failure instead of a
warning that ships a wrong contract to the frontend.

> Note: `CLAUDE.md` at the repo root holds additional working notes, but it is
> gitignored and local-only -- it won't be in your clone.

### If you run the `production` profile

Initialize the pgBackRest stanza once, before leaving it running:

```bash
docker compose exec postgres pgbackrest --stanza=tracker stanza-create
docker compose exec postgres pgbackrest --stanza=tracker backup --type=full
```

Postgres starts with `archive_mode=on`, so until the stanza exists every WAL
archive push fails and Postgres retains WAL indefinitely rather than recycling
it. Left alone, that fills the disk and the database stops.
