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
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    nodejs \
    npm \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

EXPOSE 8000

# SERVICE_TYPE: web (default), worker, or beat
CMD if [ "$SERVICE_TYPE" = "worker" ]; then \
      celery -A PartsTrackerApp worker -l info; \
    elif [ "$SERVICE_TYPE" = "beat" ]; then \
      celery -A PartsTrackerApp beat -l info; \
    else \
      python manage.py migrate --noinput && \
      python manage.py collectstatic --noinput && \
      gunicorn PartsTrackerApp.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4; \
    fi