![alt text](https://imgur.com/I0fWYqU.png)

# Caledarinho
The Mother of ALL Calendars.

## About
A web application to easily manage large team of security consultants. It has some functionalities that helps managements in the assignment and following up tasks.

## Installation Guide
1. You must have Python 3 installed.
2. Install the requirements libraries.
```
python3 -m pip install -r requirements
```
3. Set up the database connection and user (Unless you will use the defualt sqlite settings).
```python
(In the Calendarinho/settings.py file)

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases
# MySQL settings:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'Calendarinho',
#         'USER': 'USERNAME',
#         'PASSWORD': 'PASSWORD',
#         'HOST': 'localhost',
#         'PORT': '',
#     }
# }

# Local database settings (Default) 
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

```
4. Run: "makemigrations".
```
python3 manage.py makemigrations users
python3 manage.py makemigrations CalendarinhoApp
python3 manage.py makemigrations
```
5. Run: "migrate".
```
python3 manage.py migrate users
python3 manage.py migrate CalendarinhoApp
python3 manage.py migrate
```


## Images of the application:

![alt text](https://i.imgur.com/pWgx73v.png)

![alt text](https://i.imgur.com/BPab30R.png)

![alt text](https://i.imgur.com/7fGmb6H.png)

![alt text](https://i.imgur.com/yOpu0oB.png)
