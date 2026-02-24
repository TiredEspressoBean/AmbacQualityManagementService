# Stage 1: Build with Node
FROM node:20-slim AS builder

WORKDIR /app

COPY ./package.json ./
RUN npm install --legacy-peer-deps

COPY . .

ARG VITE_API_TARGET
ENV VITE_API_TARGET=$VITE_API_TARGET

RUN npm run build

# Stage 2: Serve static files with Caddy
FROM caddy:2-alpine

COPY --from=builder /app/dist /usr/share/caddy

# Caddyfile for SPA routing (fallback to index.html)
RUN echo ':80 { \
    root * /usr/share/caddy \
    try_files {path} /index.html \
    file_server \
    encode gzip \
}' > /etc/caddy/Caddyfile

EXPOSE 80

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile"]
