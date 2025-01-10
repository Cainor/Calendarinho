#!/bin/bash
# init-prod.sh

# Exit on error
set -e

# Function to log messages
log_message() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Wait for MySQL to be ready
log_message "Waiting for MySQL to be ready..."
while ! nc -z db 3306; do
    sleep 1
done
log_message "MySQL is ready!"

# Run database migrations
log_message "Running database migrations..."
python manage.py makemigrations users
python manage.py makemigrations CalendarinhoApp
python manage.py migrate users
python manage.py migrate CalendarinhoApp
python manage.py migrate

# Collect static files
log_message "Collecting static files..."
python manage.py collectstatic --no-input

# Check if superuser exists
log_message "Checking superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='${DJANGO_SUPERUSER_USERNAME:-admin}').exists():
    User.objects.create_superuser(
        username='${DJANGO_SUPERUSER_USERNAME:-admin}',
        email='${DJANGO_SUPERUSER_EMAIL:-admin@example.com}',
        password='${DJANGO_SUPERUSER_PASSWORD:-admin}',
        first_name='${DJANGO_SUPERUSER_FIRST_NAME:-Admin}',
        last_name='${DJANGO_SUPERUSER_LAST_NAME:-User}'
    )
    print('Superuser created successfully')
else:
    print('Superuser already exists')
"

# Start Gunicorn
log_message "Starting Gunicorn..."
exec gunicorn Calendarinho.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --threads 2 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    --enable-stdio-inheritance \
    --log-level debug
