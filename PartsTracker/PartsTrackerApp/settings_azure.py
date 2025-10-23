"""
Azure production settings for PartsTracker project.
"""

from .settings import *
import os

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() == 'true'

# Security settings for production
# SSL redirect handled by Azure Container Apps ingress
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
# Required for cross-origin session cookies (Static Web App + Django backend on different domains)
SESSION_COOKIE_SAMESITE = 'None'  # Allow cross-origin cookies
CSRF_COOKIE_SAMESITE = 'None'     # Allow cross-origin CSRF cookies
# Share cookies across subdomains (api.ambacinternational.com and tracker.ambacinternational.com)
SESSION_COOKIE_DOMAIN = '.ambacinternational.com'
CSRF_COOKIE_DOMAIN = '.ambacinternational.com'
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript to read CSRF token
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG

# Update ALLOWED_HOSTS from environment
allowed_hosts_str = os.environ.get('ALLOWED_HOSTS', '')
if allowed_hosts_str:
    ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_str.split(',') if host.strip()]
else:
    ALLOWED_HOSTS = ['*']  # For development/testing only

# CORS settings
cors_origins_str = os.environ.get('CORS_ALLOWED_ORIGINS', '')
if cors_origins_str:
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins_str.split(',') if origin.strip()]
else:
    CORS_ALLOWED_ORIGINS = []

CORS_ALLOW_CREDENTIALS = True

# CSRF trusted origins (for cross-domain POST requests)
csrf_trusted_origins_str = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if csrf_trusted_origins_str:
    CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_trusted_origins_str.split(',') if origin.strip()]
else:
    CSRF_TRUSTED_ORIGINS = []

# Database configuration for Azure PostgreSQL
db_host = os.environ.get('POSTGRES_HOST', 'localhost')
db_options = {}

# Enable SSL for Azure PostgreSQL, disable for local development
if 'postgres.database.azure.com' in db_host:
    db_options['sslmode'] = 'require'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'parts_tracker'),
        'USER': os.environ.get('POSTGRES_USER', 'parts_tracker_user'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
        'HOST': db_host,
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        'OPTIONS': db_options,
    }
}

# Serve static files from the app using WhiteNoise (like Docker setup but production-ready)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# WhiteNoise configuration for serving static files in production with gunicorn
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Application Insights (optional)
if os.environ.get('APPINSIGHTS_INSTRUMENTATIONKEY'):
    INSTALLED_APPS += ['applicationinsights.django']
    APPLICATION_INSIGHTS = {
        'ikey': os.environ.get('APPINSIGHTS_INSTRUMENTATIONKEY'),
    }

# Email configuration
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
if EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
    EMAIL_HOST = os.environ.get('EMAIL_HOST')
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')

# Caching with Redis (optional)
if os.environ.get('REDIS_URL'):
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.environ.get('REDIS_URL'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'default'

# Health check endpoint
HEALTH_CHECK_URL = '/health/'