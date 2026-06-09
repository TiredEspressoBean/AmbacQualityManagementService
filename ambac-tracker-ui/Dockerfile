# Stage 1: Build with Bun
# Use Bun rather than npm so the production build resolves dependencies
# the same way local dev does (we use Bun for `bun run dev` and
# `bun run build`). npm + `package.json` alone (without `package-lock.json`)
# produced a non-deterministic dep tree where sibling `@assistant-ui/*`
# packages drifted into an incompatible combination and the build failed
# on a missing `./react-shim` export.
FROM oven/bun:1 AS builder

WORKDIR /app

# Copy the lockfile too so `bun install --frozen-lockfile` produces
# the exact dep tree the developer tested against.
COPY ./package.json ./bun.lock ./
RUN bun install --frozen-lockfile

COPY . .

ARG VITE_API_TARGET
ENV VITE_API_TARGET=$VITE_API_TARGET

RUN bun run build

# Stage 2: Serve static files with Caddy
FROM caddy:2-alpine

COPY --from=builder /app/dist /usr/share/caddy
COPY Caddyfile /etc/caddy/Caddyfile

EXPOSE 80

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile"]
