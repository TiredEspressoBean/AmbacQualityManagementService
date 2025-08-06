#!/bin/bash
# Quick start script for local development

set -e

echo "🚀 Starting Parts Tracker Local Development Environment"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.local .env
    echo "✅ Created .env file. You may want to customize it for your setup."
fi

# Start the services
echo "🐳 Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Check database
if docker-compose exec -T postgres pg_isready -U parts_tracker_user -d parts_tracker_dev > /dev/null 2>&1; then
    echo "✅ Database is ready"
else
    echo "❌ Database is not ready"
fi

# Check backend
if curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
    echo "✅ Backend is ready"
else
    echo "⏳ Backend is starting up..."
fi

# Check frontend
if curl -f http://localhost:5173/health > /dev/null 2>&1; then
    echo "✅ Frontend is ready"
else
    echo "⏳ Frontend is starting up..."
fi

echo ""
echo "🎉 Local development environment is starting up!"
echo ""
echo "📱 Frontend: http://localhost:5173"
echo "🔧 Backend:  http://localhost:8000"
echo "📊 Admin:    http://localhost:8000/admin/"
echo "📚 API Docs: http://localhost:8000/api/docs/"
echo ""
echo "💡 Useful commands:"
echo "   docker-compose logs -f          # View logs"
echo "   docker-compose down             # Stop services"
echo "   docker-compose exec backend python manage.py shell  # Django shell"
echo ""
echo "🔍 To view logs: docker-compose logs -f"