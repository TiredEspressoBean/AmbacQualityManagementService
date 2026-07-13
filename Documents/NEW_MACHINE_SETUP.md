# Moving Dev to a New Computer

*(2026-07-13. Written for the current Windows 11 setup; adjust paths for
other platforms. The critical section is §1 — everything else can be
reconstructed from the repo, but §1's artifacts are gitignored and are lost
if you don't copy them.)*

## 1. What does NOT travel with `git clone` — copy these first

| Artifact | Where | Why it matters |
|---|---|---|
| `CLAUDE.md` | repo root | **Gitignored.** All the project instructions, test protocol (`--noinput`, `clean_test_dbs`), and command reference for Claude Code sessions. |
| `.claude/` (project) | repo root | Gitignored. `settings.local.json` holds the ~126-rule permission allowlist built up over months — without it every shell command prompts again. |
| `.env` | repo root | Secrets: DB credentials, `DJANGO_SECRET_KEY`, **`FIELD_ENCRYPTION_KEY`**, superuser bootstrap. `.env.example` lists the keys but not your values. |
| `ambac-tracker-ui/.env` | frontend | `VITE_LANGGRAPH_API_URL` etc. |
| `.env.docker` | repo root | Container-flavored env values. |
| `~/.claude/` (user) | home dir | Claude Code user settings (`settings.json`: model/effort/permission mode), keybindings, plans, session history. MCP server registrations live in `~/.claude.json` — chrome-devtools, memory (its graph data file too), railway, shadcn, assistant-ui. |
| Postgres data | docker volume | Only if you want to carry the dev database instead of reseeding — see §7. Usually reseeding is cleaner. |
| `.idea/` | repo root | PyCharm project config (run configurations), if you use them. |

> **Do this now, not at move time:** `FIELD_ENCRYPTION_KEY` is currently
> unset on the old machine, meaning an EPHEMERAL key is generated per
> process — sessions and encrypted fields already die on every backend
> restart. Generate a stable key, put it in `.env` on BOTH machines, and
> that whole failure class disappears:
> `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

## 2. Prerequisites (versions as of this writing)

- **Git** (+ `gh` CLI if you use it)
- **Docker Desktop** — the dev data layer runs in containers
- **Python 3.13.x** (venv lives at `PartsTracker/.venv`)
- **Bun 1.3.x** (frontend package manager/runner) and **Node 22.x**
  (used by `scripts/*.cjs` post-processing in `generate-api`)
- **Claude Code** (latest — 2.1.205+; older 2.1.17x had a Windows
  permission-prompt bug that auto-rejected edits)
- Optional: PyCharm / editor of choice

## 3. Clone + secrets

```powershell
git clone https://github.com/TiredEspressoBean/AmbacQualityManagementService.git AmbacTracker
cd AmbacTracker
# copy in from old machine (see §1):
#   CLAUDE.md, .claude\, .env, .env.docker, ambac-tracker-ui\.env
```

If recreating `.env` from scratch, start from `.env.example` and set at
minimum: `POSTGRES_USER/PASSWORD/DB`, `DJANGO_SECRET_KEY`,
`FIELD_ENCRYPTION_KEY` (stable! see §1), `DEPLOYMENT_MODE`.

## 4. Data layer

**The day-to-day dev setup: native backend + two standalone data
containers.** The Django backend and Vite dev server run natively on the
host (venv + `bun run dev`); only postgres + redis run in containers, with
host ports exposed so `localhost:5432` / `localhost:6379` work. This is what
§5–§6 assume — fast backend iteration (native `runserver` reload, direct
debugger). Bring up the two containers:

```powershell
docker run -d --name partstracker-postgres `
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=<from .env> `
  -e POSTGRES_DB=tracker_AMBAC -p 5432:5432 `
  -v partstracker-pgdata:/var/lib/postgresql/data `
  ankane/pgvector:v0.5.1

docker run -d --name partstracker-redis -p 6379:6379 redis:7-alpine
```

Notes:
- **Postgres must be the pgvector image** — the AI/doc-chunk features and a
  chunk of the test suite (`is_vector_extension_available` skips) need the
  `vector` extension. `ankane/pgvector` is the lighter dev-only equivalent of
  the compose `Dockerfile.postgres` (which also bakes in pgaudit/pgBackRest —
  audit logging + WAL archiving that dev doesn't need).
- **Redis here is passwordless** (dev backend connects to `localhost:6379`
  with no auth) — matches the native backend's default env.
- **Both must be running for the app.** Postgres is the DB; **Redis backs
  the permission cache** — with Redis down, cache-using API endpoints 500
  (`Error 10061 connecting to localhost:6379`) while a few cache-free ones
  still work, which reads confusingly like a partial outage.
- Set both to auto-restart so a reboot doesn't recreate that outage:
  `docker update --restart unless-stopped partstracker-postgres partstracker-redis`

**Occasional full-stack test (not the daily workflow):**
`docker compose --profile local up` runs *everything* in containers —
postgres + redis + backend + celery + docs + a Vite build + caddy-local
(HTTPS at `https://localhost`). Use it to exercise the app the way it
deploys (behind Caddy, celery live, prod-like wiring), not for iterating.
Its redis **requires** a password (`REDIS_PASSWORD`) and its postgres
exposes **no** host port — so it's self-contained; don't mix its config with
the standalone containers above.

## 5. Backend

```powershell
cd PartsTracker
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate            # creates the `vector` extension; NOT the others
python manage.py setup_database     # uuid-ossp + pg_trgm extensions, RBAC groups, audit triggers
python manage.py setup_defaults     # document types + approval-workflow templates
python manage.py seed_demo          # demo tenant, users (password demo123), demo stories
python manage.py setup_notification_rules
python manage.py runserver          # :8000
```

**Why `setup_database` matters:** `migrate` only creates the `vector`
extension (migration 0001). `uuid-ossp` / `pg_trgm`, the RBAC groups, and the
audit-immutability triggers come from `setup_database` — skip it and the app
comes up broken in non-obvious ways. (The `docker compose --profile local`
backend runs the equivalent on boot; the native workflow must run it by
hand.) It also installs RLS policies **only if `ENABLE_RLS=true`** — which
defaults to **false** in dev, so the app runs as the `postgres` superuser
with app-layer tenant scoping (SecureManager ContextVar) and you do *not*
need the `partstracker_app` role from `init-db.sql`.

Demo logins: `admin@demo.ambac.com` (Tenant Admin), `sarah.qa@demo.ambac.com`
(QA — lands on the QA inbox), `mike.ops@demo.ambac.com` (operator) — all
`demo123`.

**Optional — AI chat:** the AI-chat feature talks to a separate LangGraph
service (`VITE_LANGGRAPH_API_URL`, `init-langgraph-db.sql`), not the Django
backend. It's not part of core setup; skip it unless you're specifically
working on AI chat.

## 6. Frontend

```powershell
cd ambac-tracker-ui
bun install
bun run dev            # :5173, proxies /api → :8000
```

Generated API client/types (`src/lib/api/generated*.ts`) are committed, so no
regen is needed to start. After backend serializer changes:
`bun run generate-api && bun run typecheck` (see
`Documents/API_TYPE_GENERATION.md`).

## 7. Carrying the dev database (optional)

Reseeding (§5) is usually the right call. To carry data instead:

```powershell
# old machine
docker exec partstracker-postgres pg_dump -U <user> -Fc tracker_AMBAC > tracker.dump
# new machine (after §4, before migrate)
docker exec -i partstracker-postgres pg_restore -U <user> -d tracker_AMBAC --clean < tracker.dump
```

Note: encrypted fields only survive if `FIELD_ENCRYPTION_KEY` matches the key
that wrote them — another reason to pin it (§1).

**Media files are separate from the DB dump** — `PartsTracker/media/`
(~27M, gitignored) travels with neither `git clone` nor the `pg_dump`. But
most of it is reproducible, so you rarely need to copy it:
- **Demo/test 3D models (benchy) — don't bother.** `seed_demo` regenerates
  every `media/models/3DBenchy_*.glb` from `PartsTracker/seed_assets/models/
  3DBenchy.glb`, which **is committed to git**. The `media/models/` copies
  are derived artifacts.
- **`parts_docs/` / `lot_certificates/`** back uploaded-document DB rows —
  only worth copying if you're carrying the actual DB (else reseeding makes
  its own, or the rows 404).
- **`tenant_logos/`** — the one thing seeding won't recreate; copy it if
  you hand-uploaded a custom logo.

So: reseeding ⇒ skip `media/` entirely; carrying real data ⇒ copy `media/`
alongside the `pg_dump`.

## 8. Verify

- `Invoke-WebRequest http://localhost:8000/health/` → 200
- Log in at `http://localhost:5173` as `sarah.qa@demo.ambac.com` → lands on
  the QA inspection inbox with live data; the notification bell renders
- `cd PartsTracker; python manage.py test Tracker.tests.test_inspection_inbox --keepdb` → OK
- `cd ambac-tracker-ui; bun run typecheck` → clean
- Full suite when needed: `python manage.py test --parallel 4 --noinput`
  (always `--noinput`; if "database test_… already exists" →
  `python manage.py clean_test_dbs`)

## 9. Known gotchas (all learned the hard way)

- **Redis down ⇒ mysterious 500s** on cache-using endpoints only (§4).
- **Backend restart with ephemeral `FIELD_ENCRYPTION_KEY`** logs everyone
  out and orphans encrypted data — pin the key (§1).
- **Killed test runs orphan test DBs**; the next run then hangs (without
  `--noinput`) or fails ("already exists"). Recovery:
  `python manage.py clean_test_dbs`. Kill runaway test processes by command
  line (`manage.py test`), never by process name — the dev server is python
  too.
- **Claude Code**: if edits start auto-rejecting with no visible prompt,
  fully restart the process (don't `--resume`) and check for updates —
  known Windows prompt-channel bug class.
