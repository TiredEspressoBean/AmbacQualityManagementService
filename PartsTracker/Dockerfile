FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install Tailwind globally
RUN npm install -g tailwindcss

# Copy the Django project code
COPY . /app/

EXPOSE 8000

# Use the command from docker-compose for development
# For production, use: CMD ["gunicorn", "PartsTrackerApp.wsgi:application", "--bind", "0.0.0.0:8000"]FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install Tailwind globally
RUN npm install -g tailwindcss

# Copy the Django project files (includes PartsTrackerApp)
COPY . /app/

EXPOSE 8000

# Use the command from docker-compose for development
# For production, use: CMD ["gunicorn", "myproject.wsgi:application", "--bind", "0.0.0.0:8000"]