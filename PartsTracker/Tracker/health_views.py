from django.http import JsonResponse, HttpResponse
from django.db import connection
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

def health_check(request):
    """
    Health check endpoint for Azure Container Apps
    """
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            
        # Optional: Check cache if Redis is configured
        try:
            cache.set('health_check', 'ok', 30)
            cache.get('health_check')
        except Exception as e:
            logger.warning(f"Cache check failed: {e}")
        
        return HttpResponse("healthy", status=200, content_type="text/plain")
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HttpResponse("unhealthy", status=503, content_type="text/plain")

def ready_check(request):
    """
    Readiness check endpoint
    """
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM django_migrations")
            
        return HttpResponse("ready", status=200, content_type="text/plain")
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return HttpResponse("not ready", status=503, content_type="text/plain")