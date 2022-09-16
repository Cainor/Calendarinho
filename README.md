![alt text](https://imgur.com/I0fWYqU.png)

# Caledarinho
The Mother of ALL Calendars.

## About
A web application to easily manage large team of consultants. It has some functionalities that helps managements in the assignment and following up tasks.

## Installation Guide
1. You must have Python 3 installed.
2. Install the requirements libraries:
```
python -m pip install -r requirements
```
3. Go through the ```Calendarinho/settings.py``` and set your settings, specially the Database:
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
6. Create the admin user:
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
