# Serving the Documentation Site

This page covers how the documentation you're reading is built and served, and
what to do when `/docs/` stops working.

## How it works

The docs are **static HTML**, built from the Markdown in `docs/` by MkDocs, and
served by Caddy alongside the application.

```
docs/ + mkdocs.yml
        │
        ▼
  docs-builder            one-shot container: mkdocs build
        │
        ▼
  docs-dist  (volume)     the rendered site
        │
        ▼
  caddy  /srv/docs        served at /docs/
```

Three pieces have to line up:

| Piece | Where | Role |
|-------|-------|------|
| `docs-builder` | `docker-compose.yml` | Runs `mkdocs build` into the `docs-dist` volume |
| `docs-dist` | named volume | Holds the rendered site between runs |
| `handle_path /docs/*` | `conf/Caddyfile` | Serves it from `/srv/docs` |

## Updating the docs

!!! warning "Editing Markdown is not enough"
    `docs-builder` is a **one-shot** container that runs at stack bring-up. It
    does not watch for changes. Editing anything under `docs/` has no effect on
    the served site until the builder runs again.

To publish changes:

```bash
docker compose --profile production run --rm docs-builder
```

The volume is rewritten in place, and Caddy picks the new files up on the next
request — no restart needed.

## When /docs/ returns the app instead of the docs

A request that falls through to the SPA catch-all returns `index.html` with a
**200**, so the docs URL renders the application rather than erroring. Two
causes:

**Missing trailing slash.** `handle_path /docs/*` matches `/docs/…` but not a
bare `/docs`. A redirect handles this:

```
handle /docs {
    redir * /docs/ 301
}
```

**The catch-all won.** Caddy orders `handle` blocks by matcher specificity, so
`/docs/*` should always beat the bare `handle`. If it isn't, check that the
config Caddy actually loaded is the one you edited.

## When /docs/ returns 404

The route matched but there are no files. Check inside the container:

```bash
docker compose exec caddy ls /srv/docs | head
```

| Result | Meaning |
|--------|---------|
| `index.html`, `search/`, section directories | The site is there; the problem is elsewhere |
| Empty | `docs-builder` hasn't run, or wrote to a different volume |
| `No such file or directory` | The volume isn't mounted into the running container |

For the last case, confirm what the running container actually has:

```bash
docker inspect $(docker compose --profile production ps -q caddy) \
  --format '{{range .Mounts}}{{.Name}} -> {{.Destination}}{{"\n"}}{{end}}'
```

!!! danger "Don't mount the docs inside the SPA root"
    `docs-dist` is mounted at **`/srv/docs`**, deliberately outside
    `/usr/share/caddy`. It used to be nested at `/usr/share/caddy/docs`, inside
    the `frontend-dist` volume, and that caused a failure that is very hard to
    diagnose:

    A nested mount is attached when the container is **created**, and depends on
    its mountpoint directory continuing to exist in the parent volume. Rebuilding
    the frontend clears `frontend-dist`, removing that directory and orphaning
    the mount in the already-running container. `docker inspect` still lists the
    mount while `ls` inside the container reports "No such file or directory",
    and `/docs/` 404s until Caddy is recreated.

    The symptom appears when the **frontend** is rebuilt, not when anything
    about the docs changes — which is what makes it so confusing. Keeping the
    mount outside the SPA root avoids it entirely.

## Verifying a deployment

```bash
curl -sk -o /dev/null -w "%{http_code}\n" https://your-domain/docs     # expect 301
curl -sk -o /dev/null -w "%{http_code}\n" https://your-domain/docs/    # expect 200
```

## Checking the build locally

You can run the same build the container runs, without a full stack:

```bash
docker run --rm \
  -v "$PWD/mkdocs.yml:/docs/mkdocs.yml:ro" \
  -v "$PWD/docs:/docs/docs:ro" \
  -w /docs python:3.12-slim \
  sh -c "pip install --no-cache-dir mkdocs pymdown-extensions && mkdocs build --site-dir /tmp/out"
```

MkDocs reports pages missing from the `nav` configuration and links pointing at
anchors that don't exist. Both are `INFO` rather than errors, so read the output
even when the build succeeds.

## Next Steps

- **[Railway Deployment](railway.md)** - Deploying the application itself
