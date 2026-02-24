FROM python:3.12-slim AS builder

WORKDIR /docs

# Install MkDocs and extensions
RUN pip install --no-cache-dir mkdocs pymdown-extensions

# Copy docs source
COPY mkdocs.yml ./
COPY docs/ ./docs/

# Build documentation
RUN mkdocs build --site-dir /docs/site

# Stage 2: Serve with lightweight static server
FROM caddy:2-alpine

COPY --from=builder /docs/site /usr/share/caddy

EXPOSE 80

CMD ["caddy", "file-server", "--root", "/usr/share/caddy", "--listen", ":80"]
