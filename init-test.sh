#!/bin/bash
# wait-for-db.sh

# Wait for MySQL to be ready
echo "Waiting for MySQL to be ready..."
while ! nc -z db 3306; do
  sleep 1
done
echo "MySQL is ready!"

# Run the Django commands
python manage.py makemigrations users
python manage.py makemigrations CalendarinhoApp
python manage.py migrate users
python manage.py migrate CalendarinhoApp
python manage.py migrate
export DJANGO_SUPERUSER_USERNAME=admin
export DJANGO_SUPERUSER_PASSWORD=admin
export DJANGO_SUPERUSER_EMAIL=admin@example.com
export DJANGO_SUPERUSER_FIRST_NAME=Mohammad
export DJANGO_SUPERUSER_LAST_NAME=Almazroa
python manage.py createsuperuser --noinput
# Add first_name and last_name
python manage.py shell -c "
import os
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.get(username=os.getenv('DJANGO_SUPERUSER_USERNAME'))
user.first_name = os.getenv('DJANGO_SUPERUSER_FIRST_NAME')
user.last_name = os.getenv('DJANGO_SUPERUSER_LAST_NAME')
user.save()
"
python manage.py 
python manage.py runserver 0.0.0.0:8000