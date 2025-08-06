#!/bin/bash
# Script to generate secure environment variables for Parts Tracker

set -e

echo "🔐 Generating secure environment variables for Parts Tracker"

# Function to generate a random password
generate_password() {
    local length=${1:-32}
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
}

# Function to generate Django secret key
generate_django_secret() {
    python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())" 2>/dev/null || \
    openssl rand -base64 50 | tr -d "=+/"
}

# Environment selection
echo "Select environment:"
echo "1) Local Development"
echo "2) Local Production"
echo "3) Azure Production"
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        ENV_FILE=".env.local"
        ENV_NAME="Local Development"
        ;;
    2)
        ENV_FILE=".env.prod.local"
        ENV_NAME="Local Production"
        ;;
    3)
        ENV_FILE=".env.production"
        ENV_NAME="Azure Production"
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo "📝 Generating secrets for $ENV_NAME environment..."

# Generate secrets
DJANGO_SECRET=$(generate_django_secret)
POSTGRES_PASSWORD=$(generate_password 24)
POWERBI_PASSWORD=$(generate_password 24)

# Create backup if file exists
if [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    echo "📋 Backed up existing $ENV_FILE"
fi

# Base configuration based on environment
case $choice in
    1)
        cat > "$ENV_FILE" << EOF
# Local Development Environment Configuration
# Generated on $(date)

# Django Configuration
DJANGO_SECRET_KEY=$DJANGO_SECRET
DJANGO_DEBUG=True
DJANGO_SETTINGS_MODULE=PartsTrackerApp.settings

# Database Configuration (local PostgreSQL via Docker)
POSTGRES_DB=parts_tracker_dev
POSTGRES_USER=parts_tracker_user
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Frontend Configuration
VITE_API_TARGET=http://localhost:8000

# Local Host Configuration
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0,backend
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8080

# Development Settings
# Email backend for development (prints to console)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Security Settings (relaxed for development)
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False

# Power BI Integration
POWERBI_PASSWORD=$POWERBI_PASSWORD
EOF
        ;;
    2)
        read -p "Enter your Linux server IP: " SERVER_IP
        cat > "$ENV_FILE" << EOF
# Local Production Testing Environment Configuration
# Generated on $(date)

# Django Configuration
DJANGO_SECRET_KEY=$DJANGO_SECRET
DJANGO_DEBUG=False
DJANGO_SETTINGS_MODULE=PartsTrackerApp.settings_azure

# Database Configuration (local PostgreSQL for production testing)
POSTGRES_DB=parts_tracker_prod_test
POSTGRES_USER=parts_tracker_user
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Frontend Configuration
VITE_API_TARGET=http://$SERVER_IP:8000

# Local Production Host Configuration
ALLOWED_HOSTS=$SERVER_IP,localhost,127.0.0.1,backend,frontend
CORS_ALLOWED_ORIGINS=http://$SERVER_IP,http://$SERVER_IP:80,http://$SERVER_IP:8080

# Production-like Email Configuration (optional - use console for testing)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Security Settings (production-like but adapted for local testing)
SECURE_SSL_REDIRECT=False
SECURE_BROWSER_XSS_FILTER=True
SECURE_CONTENT_TYPE_NOSNIFF=True
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False

# Power BI Integration
POWERBI_PASSWORD=$POWERBI_PASSWORD
EOF
        ;;
    3)
        read -p "Enter your backend FQDN (e.g., myapp-backend.eastus.azurecontainerapps.io): " BACKEND_FQDN
        read -p "Enter your frontend FQDN (e.g., myapp-frontend.eastus.azurecontainerapps.io): " FRONTEND_FQDN
        read -p "Enter your PostgreSQL server name (e.g., myapp-postgres): " POSTGRES_SERVER
        cat > "$ENV_FILE" << EOF
# Production Environment Variables for Azure Container Apps
# Generated on $(date)

# Django Configuration
DJANGO_SECRET_KEY=$DJANGO_SECRET
DJANGO_DEBUG=False
DJANGO_SETTINGS_MODULE=PartsTrackerApp.settings_azure

# Database Configuration (Azure Database for PostgreSQL Flexible Server)
POSTGRES_DB=parts_tracker
POSTGRES_USER=parts_tracker_user
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_HOST=$POSTGRES_SERVER.postgres.database.azure.com
POSTGRES_PORT=5432
DATABASE_URL=postgresql://parts_tracker_user:$POSTGRES_PASSWORD@$POSTGRES_SERVER.postgres.database.azure.com:5432/parts_tracker

# Allowed Hosts (Replace with your actual domains)
ALLOWED_HOSTS=$BACKEND_FQDN,localhost,127.0.0.1

# CORS Configuration (Replace with your actual frontend domain)
CORS_ALLOWED_ORIGINS=https://$FRONTEND_FQDN

# Frontend Configuration
VITE_API_TARGET=https://$BACKEND_FQDN

# Azure Storage (Optional - for static/media files)
# AZURE_STORAGE_ACCOUNT_NAME=your-storage-account
# AZURE_STORAGE_ACCOUNT_KEY=your-storage-key
# AZURE_STORAGE_CONTAINER_NAME_STATIC=static
# AZURE_STORAGE_CONTAINER_NAME_MEDIA=media

# Email Configuration (Optional)
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST=smtp.sendgrid.net
# EMAIL_PORT=587
# EMAIL_USE_TLS=True
# EMAIL_HOST_USER=apikey
# EMAIL_HOST_PASSWORD=your-sendgrid-api-key

# Security Settings
SECURE_SSL_REDIRECT=True
SECURE_BROWSER_XSS_FILTER=True
SECURE_CONTENT_TYPE_NOSNIFF=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Application Insights (Optional)
# APPINSIGHTS_INSTRUMENTATIONKEY=your-app-insights-key

# Power BI Integration
POWERBI_PASSWORD=$POWERBI_PASSWORD
EOF
        ;;
esac

echo "✅ Environment file $ENV_FILE created successfully!"
echo ""
echo "🔒 Generated secrets:"
echo "   Django Secret Key: [HIDDEN - 50 characters]"
echo "   PostgreSQL Password: [HIDDEN - 24 characters]"
echo "   Power BI Password: [HIDDEN - 24 characters]"
echo ""
echo "📋 Next steps:"
echo "   1. Review and customize $ENV_FILE as needed"
echo "   2. Never commit this file to version control"
echo "   3. Share secrets securely with your team"
echo "   4. Set up backup/recovery for these credentials"
echo ""
echo "🔐 Security reminders:"
echo "   - Store backup of secrets in secure password manager"
echo "   - Rotate passwords regularly"
echo "   - Use different passwords for each environment"
echo "   - Monitor access logs for unauthorized usage"
echo ""

# Set proper permissions
chmod 600 "$ENV_FILE"
echo "🛡️  Set restrictive permissions (600) on $ENV_FILE"