# Parts Tracker QMS

Quality Management System for manufacturing parts tracking.

## Quick Start

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Update your password:**
   ```bash
   # Edit .env and set:
   POSTGRES_PASSWORD=your-secure-password
   ```

3. **Start the application:**
   ```bash
   docker-compose up -d
   ```

4. **Access the application:**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000/admin
   - Database: localhost:5432

## Development

The application uses:
- **Backend:** Django + PostgreSQL
- **Frontend:** React + Vite
- **Database:** PostgreSQL 16

## Environment Variables

Required:
- `POSTGRES_PASSWORD` - Database password

Optional:
- `POSTGRES_DB` - Database name (default: tracker_AMBAC)
- `POSTGRES_USER` - Database user (default: postgres)
- `DJANGO_SECRET_KEY` - Django secret key
- `VITE_API_TARGET` - API endpoint for frontend (default: http://localhost:8000)

## Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild and start (after code changes)
docker-compose up -d --build

# Reset everything (including database)
docker-compose down -v && docker-compose up -d --build
```