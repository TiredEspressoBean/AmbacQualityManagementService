FROM python:3.12-slim

# python:3.12-slim is Debian-based (glibc), required for:
# - cascadio: OpenCASCADE bindings for STEP→GLB conversion (manylinux wheels)
# - trimesh: 3D mesh processing
# - fast-simplification: Mesh decimation (manylinux wheels)
# DO NOT use Alpine (musl) - cascadio wheels are not available for musl

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
# fonts-noto-core: Noto Sans + Noto Serif + Noto Sans Mono for Typst reports.
# Typst scans /usr/share/fonts automatically, so no extra configuration needed.
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    nodejs \
    npm \
    cron \
    fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Vendor Typst Universe packages (cetz, cetz-plot, diagraph, oxifmt).
# Placed at the default package cache path so Typst resolves
# `@preview/<pkg>:<version>` imports without network access — required
# for on-prem-behind-firewall deployments.
COPY typst_packages /root/.cache/typst/packages/

# Copy project files
COPY . .

EXPOSE 8000

# SERVICE_TYPE: web (default), worker, or beat
#
# --access-logfile - puts the request log on STDOUT. Without it gunicorn logs no
# requests at all, which is what made a handful of production 5xx impossible to
# attribute: the proxy counted them and nothing recorded which endpoint failed.
#
# --log-level warning is about log SEVERITY, not volume. gunicorn's errorlog
# already defaults to '-' (stderr), and its startup lines are INFO on that
# logger -- so an ordinary boot wrote 'Starting gunicorn' to stderr and Railway
# tagged every normal deploy as severity=error. Raising the level drops that
# chatter and leaves stderr for real problems (worker timeouts, boot failures),
# so red means something. It does NOT affect request logging: glogging.py pins
# access_log to INFO unconditionally and writes it to stdout.
# (No --error-logfile here on purpose: '-'/stderr is already the default.)
# Django tracebacks are handled separately, by the LOGGING dict in settings.py:
# its default console handler carries require_debug_true and is off whenever
# DEBUG=False, so unhandled view exceptions would otherwise go only to
# mail_admins (unconfigured). Both halves are needed: this flag for which
# request failed, that dict for why.
CMD if [ "$SERVICE_TYPE" = "worker" ]; then \
      celery -A PartsTrackerApp worker -l info; \
    elif [ "$SERVICE_TYPE" = "beat" ]; then \
      celery -A PartsTrackerApp beat -l info; \
    else \
      python manage.py migrate --noinput && \
      python manage.py setup_defaults && \
      python manage.py setup_database && \
      python manage.py collectstatic --noinput && \
      gunicorn PartsTrackerApp.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4 \
        --access-logfile - --log-level warning; \
    fi