FROM python:3.12-slim

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

# Create entrypoint script
RUN echo '#!/bin/sh\n\
python manage.py makemigrations\n\
python manage.py migrate\n\
python manage.py create_temp_admin\n\
python manage.py tailwind install\n\
python manage.py tailwind build\n\
python manage.py crontab add\n\
service cron start\n\
exec python manage.py runserver 0.0.0.0:8000' > /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

CMD ["/app/entrypoint.sh"]