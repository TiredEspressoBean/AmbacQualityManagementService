# Local Linux Production Deployment Guide

This guide is specifically for deploying your Django + React + PostgreSQL application on a local Linux server (Ubuntu/Debian) for production testing or staging environments.

## Prerequisites (Linux Server)

1. **Update system packages**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Install Docker & Docker Compose**
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   sudo usermod -aG docker $USER
   newgrp docker

   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose

   # Verify installation
   docker --version
   docker-compose --version
   ```

3. **Install additional tools**
   ```bash
   sudo apt install -y git curl nano htop
   ```

## Deployment Options

### Option 1: Direct Docker Compose Deployment

#### Step 1: Transfer Files to Linux Server

**From Windows (using WSL, Git Bash, or PowerShell):**
```bash
# Option A: Git clone (recommended)
git clone <your-repo-url>
cd AmbacTracker

# Option B: SCP from Windows
scp -r C:\Users\camer\AmbacTracker user@your-server:/home/user/
ssh user@your-server
cd AmbacTracker

# Option C: Use rsync (if available)
rsync -avz /mnt/c/Users/camer/AmbacTracker/ user@your-server:/home/user/AmbacTracker/
```

#### Step 2: Configure Environment

```bash
# Create production environment file
cp .env.production .env.prod.linux

# Edit environment file for your Linux server
nano .env.prod.linux
```

**Example `.env.prod.linux`:**
```bash
# Django Configuration
DJANGO_SECRET_KEY=your-super-secret-key-min-50-chars-for-linux-production-change-this
DJANGO_DEBUG=False
DJANGO_SETTINGS_MODULE=PartsTrackerApp.settings_azure

# Database Configuration
POSTGRES_DB=parts_tracker_prod
POSTGRES_USER=parts_tracker_user
POSTGRES_PASSWORD=YourStrongLinuxPassword123-CHANGE-THIS
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Network Configuration (adjust IP for your server)
VITE_API_TARGET=http://YOUR_SERVER_IP:8000
ALLOWED_HOSTS=YOUR_SERVER_IP,localhost,127.0.0.1,backend,your-domain.com
CORS_ALLOWED_ORIGINS=http://YOUR_SERVER_IP,https://your-domain.com

# Security Settings
SECURE_SSL_REDIRECT=False  # Set to True if using HTTPS
SECURE_BROWSER_XSS_FILTER=True
SECURE_CONTENT_TYPE_NOSNIFF=True
SESSION_COOKIE_SECURE=False  # Set to True if using HTTPS
CSRF_COOKIE_SECURE=False    # Set to True if using HTTPS

# Email Configuration (optional)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=your-smtp-server.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@domain.com
EMAIL_HOST_PASSWORD=your-email-password-change-this
```

#### Step 3: Deploy Application

```bash
# Make scripts executable
chmod +x start-local.sh

# Build and start production services
docker-compose -f docker-compose.prod.yml --env-file .env.prod.linux up -d --build

# Check services status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

#### Step 4: Initialize Database

```bash
# Run migrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Create superuser
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# Collect static files
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

#### Step 5: Configure Firewall and Access

```bash
# Configure UFW firewall (Ubuntu)
sudo ufw allow 22      # SSH
sudo ufw allow 80      # HTTP
sudo ufw allow 443     # HTTPS
sudo ufw allow 8000    # Django (if needed)
sudo ufw enable

# For CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

### Option 2: Production-Ready with Nginx Reverse Proxy

#### Step 1: Install Nginx

```bash
# Ubuntu/Debian
sudo apt install nginx -y

# CentOS/RHEL
sudo yum install nginx -y
# or
sudo dnf install nginx -y

# Start and enable Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

#### Step 2: Configure Nginx

```bash
# Create Nginx configuration
sudo nano /etc/nginx/sites-available/parts-tracker
```

**Nginx Configuration (`/etc/nginx/sites-available/parts-tracker`):**
```nginx
server {
    listen 80;
    server_name YOUR_SERVER_IP_OR_DOMAIN;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Frontend (React)
    location / {
        proxy_pass http://localhost:80;  # Frontend container
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Admin panel
    location /admin/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files (if not using CDN)
    location /static/ {
        alias /var/www/parts-tracker/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /var/www/parts-tracker/media/;
        expires 1M;
        add_header Cache-Control "public";
    }

    # Health check
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

#### Step 3: Enable Nginx Site

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/parts-tracker /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

#### Step 4: Setup SSL with Let's Encrypt (Optional)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Test auto-renewal
sudo certbot renew --dry-run

# Auto-renewal cron job
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Option 3: Systemd Service for Auto-Start

#### Step 1: Create Systemd Service

```bash
sudo nano /etc/systemd/system/parts-tracker.service
```

**Service file content:**
```ini
[Unit]
Description=Parts Tracker Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/user/AmbacTracker
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml --env-file .env.prod.linux up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0
User=user
Group=docker

[Install]
WantedBy=multi-user.target
```

#### Step 2: Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable parts-tracker.service

# Start service
sudo systemctl start parts-tracker.service

# Check status
sudo systemctl status parts-tracker.service

# View logs
sudo journalctl -u parts-tracker.service -f
```

## Environment-Specific Configurations

### Development on Windows

Create `.env.windows.dev`:
```bash
# Windows Development Environment
DJANGO_SECRET_KEY=dev-secret-key-for-windows-change-this
DJANGO_DEBUG=True
DJANGO_SETTINGS_MODULE=PartsTrackerApp.settings

# Use localhost for Windows development
POSTGRES_HOST=localhost
VITE_API_TARGET=http://localhost:8000
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Production on Linux

Create `.env.linux.prod`:
```bash
# Linux Production Environment
DJANGO_SECRET_KEY=prod-secret-key-for-linux-server-change-this
DJANGO_DEBUG=False
DJANGO_SETTINGS_MODULE=PartsTrackerApp.settings_azure

# Use container networking for Linux production
POSTGRES_HOST=postgres
VITE_API_TARGET=http://YOUR_LINUX_SERVER_IP:8000
ALLOWED_HOSTS=YOUR_LINUX_SERVER_IP,your-domain.com,backend
CORS_ALLOWED_ORIGINS=http://YOUR_LINUX_SERVER_IP,https://your-domain.com
```

## Monitoring and Maintenance

### System Monitoring

```bash
# Monitor Docker containers
docker stats

# Monitor system resources
htop

# Monitor disk usage
df -h

# Monitor logs
docker-compose -f docker-compose.prod.yml logs -f

# Monitor specific service
docker-compose -f docker-compose.prod.yml logs -f backend
```

### Backup Strategy

```bash
# Create backup script
nano backup-parts-tracker.sh
```

**Backup script content:**
```bash
#!/bin/bash
# Parts Tracker Backup Script

BACKUP_DIR="/home/user/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U parts_tracker_user parts_tracker_prod > $BACKUP_DIR/database_$DATE.sql

# Backup media files
tar -czf $BACKUP_DIR/media_$DATE.tar.gz -C /var/lib/docker/volumes/ambactracker_media_files/_data .

# Cleanup old backups (keep last 7 days)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

```bash
# Make executable and schedule
chmod +x backup-parts-tracker.sh

# Add to crontab (daily backup at 2 AM)
crontab -e
# Add: 0 2 * * * /home/user/AmbacTracker/backup-parts-tracker.sh >> /var/log/parts-tracker-backup.log 2>&1
```

### Update Procedure

```bash
# Update application
cd /home/user/AmbacTracker

# Pull latest changes
git pull origin main

# Rebuild containers
docker-compose -f docker-compose.prod.yml build --no-cache

# Update with zero downtime
docker-compose -f docker-compose.prod.yml up -d

# Run migrations if needed
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Collect static files
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

## Troubleshooting

### Common Linux Issues

#### Permission Issues
```bash
# Fix Docker permissions
sudo usermod -aG docker $USER
newgrp docker

# Fix file permissions
sudo chown -R $USER:$USER /home/user/AmbacTracker
```

#### Port Conflicts
```bash
# Check what's using a port
sudo netstat -tulpn | grep :80
sudo lsof -i :8000

# Kill process
sudo kill -9 <PID>
```

#### Container Issues
```bash
# Check container logs
docker-compose -f docker-compose.prod.yml logs backend

# Restart specific service
docker-compose -f docker-compose.prod.yml restart backend

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build backend
```

#### Database Issues
```bash
# Check database connection
docker-compose -f docker-compose.prod.yml exec postgres pg_isready -U parts_tracker_user -d parts_tracker_prod

# Connect to database
docker-compose -f docker-compose.prod.yml exec postgres psql -U parts_tracker_user -d parts_tracker_prod

# Reset database (CAUTION: Data loss)
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d postgres
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate
```

### Performance Optimization

```bash
# Enable Docker logging driver
# Add to docker-compose.prod.yml:
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"

# Optimize PostgreSQL
# Create custom postgres.conf and mount as volume
```

## Security Hardening

### Server Security
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Configure automatic security updates
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure -plow unattended-upgrades

# Install fail2ban
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Disable root login
sudo nano /etc/ssh/sshd_config
# Set: PermitRootLogin no
# Set: PasswordAuthentication no (if using SSH keys)
sudo systemctl restart ssh
```

### Application Security
```bash
# Ensure environment variables are secure
chmod 600 .env.prod.linux

# Use secrets management (optional)
docker secret create django_secret_key /path/to/secret
```

This guide provides comprehensive instructions for deploying your application on a Linux server while developing on Windows.