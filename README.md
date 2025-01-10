<p align="center">
  <img src="https://imgur.com/I0fWYqU.png">
</p>

# Caledarinho

The Mother of All Calendars. A web application to easily manage large team of services providers.

## About

Enough with crowded shared calendars, we need a better way to manage our team's tasks and services. This is where Calendarinho comes in. With Calendarinho, you can easily have an eagle view of your team's calendars and tasks, and manage them all in one place.

## Installation Guide

### Docker (Testing Environment)

1. Clone the repository:

```bash
git clone https://github.com/Cainor/Calendarinho.git
cd Calendarinho
```

2. Build and Start the Docker image:

```bash
docker-compose -f docker-compose.test.yml up -d --build
```

3. Wait for 1 min for the database to be ready.
4. Go to http://localhost:8000 and login with the credentials:

```
admin
admin
```

### Docker (Production Environment)

1. Clone the repository:

```bash
git clone https://github.com/Cainor/Calendarinho.git
cd Calendarinho
```

2. Create a copy of the `.env.example` file and rename it to `.env.prod`:

```bash
cp .env.example .env.prod
```

3. Edit the `.env.prod` file and set the environment variables with your settings.
4. Add your SSL certificate to ssl folder. Must be called "certificate.crt"

```
ssl/certificate.crt
```

4. If you don't have a SSL certificate, you can generate one with the following command:

```bash
bash generate-cert.sh
```

5. Build and Start the Docker image:

```bash
docker-compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

6. Wait for 1 min for the database to be ready.
7. Go to http://localhost and login with the credentials you set in the `.env.prod` file.

### Manual

1. You must have Python 3 installed.
2. Install the requirements libraries:

```
python -m pip install -r requirements
```

3. Go through the `Calendarinho/settings.py` and set your settings, specially the Database:

```python
(In the Calendarinho/settings.py file)

# MySQL Database:
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'Calendarinho',
#         'USER': 'Calendarinhouser',
#         'PASSWORD': 'Calendarinhopassword',
#         'HOST': 'localhost',
#         'PORT': '',
#     }
# }

# sqlite3 Database:
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

```

Also, in the same file, you can setup the Email settings:

```python
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# Gamil Settings (You must enable "Less-Secure-App" in Google account settings)
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = os.environ.get('EMAIL_USER')
# EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASSWORD')
```

4. Run: "makemigrations":

```
python manage.py makemigrations users
python manage.py makemigrations CalendarinhoApp
python manage.py makemigrations
```

5. Run: "migrate":

```
python manage.py migrate users
python manage.py migrate CalendarinhoApp
python manage.py migrate
```

6. Run: "collectstatic"

```
python manage.py collectstatic
```

7. Create the admin user:

```
python manage.py createsuperuser
```

## Images of the application:

![alt text](https://imgur.com/Ah7wPAS.png)

![alt text](https://imgur.com/a6tJoQM.png)

![alt text](https://imgur.com/1Pe0oBo.png)

![alt text](https://imgur.com/8wwEDlQ.png)

![alt text](https://imgur.com/R8CTRyg.png)

![alt text](https://imgur.com/qb0yj3Z.png)

## Things to do:

- [x] Before adding item, do frontend check for fields.
- [ ] Add the ability to update or cancel leaves without the need for admin
