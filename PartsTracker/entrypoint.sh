#!/bin/sh
set -e

echo "Starting Django application..."

# Run Django setup commands
python manage.py makemigrations
python manage.py migrate
python manage.py create_temp_admin
python manage.py tailwind install
python manage.py tailwind build
python manage.py crontab add

# Start cron service
service cron start

# Start Django development server
exec python manage.py runserver 0.0.0.0:8000