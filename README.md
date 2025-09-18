<p align="center">
  <img src="https://imgur.com/I0fWYqU.png">
</p>

# Calendarinho

[![License: MIT](https://img.shields.io/badge/License-AGPLv3-Green)](https://opensource.org/license/agpl-v3)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.0+-green.svg)](https://www.djangoproject.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

The Mother of All Calendars. A web application to easily manage large team of services providers.

## Table of Contents

- [About](#about)
- [Tech Stack](#tech-stack)
- [Installation Guide](#installation-guide)
  - [Docker (Testing Environment)](#docker-testing-environment)
  - [Docker (Production Environment)](#docker-production-environment)
  - [Manual Installation](#manual-installation)
- [Active Directory Authentication](#active-directory-authentication-setup)
- [Screenshots](#screenshots)

## About

Enough with crowded shared calendars, we need a better way to manage our team's tasks and services. This is where Calendarinho comes in. With Calendarinho, you can easily have an eagle view of your team's calendars and tasks, and manage them all in one place.

## Tech Stack

- **Backend**: Django (Python 3.8+)
- **Database**: MySQL / SQLite
- **Frontend**: HTML, CSS, JavaScript
- **Authentication**: Django Auth + LDAP/Active Directory support
- **Deployment**: Docker & Docker Compose
- **Web Server**: Nginx (in production)

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

3. Wait for 1 min (Could take longer if it is the first time) for the database to be ready.
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
python -m pip install -r requirements.txt
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

## Active Directory Authentication Setup

Calendarinho supports both local authentication and Active Directory (AD) authentication. Users can log in with either their local account credentials or their AD credentials seamlessly.

### Configuration Steps

#### Step 1: Enable AD Authentication

Edit your settings file (`Calendarinho/settings/base.py` for the current setup) and set:

```python
ENABLE_AD_AUTHENTICATION = True
```

#### Step 2: Configure LDAP/AD Server Settings

Add your Active Directory server configuration:

```python
# LDAP/AD Server Configuration
AUTH_LDAP_SERVER_URI = "ldap://your-domain-controller.company.com"
AUTH_LDAP_BIND_DN = "cn=service-account,ou=Service Accounts,dc=company,dc=com"
AUTH_LDAP_BIND_PASSWORD = "your-service-account-password"

# User search configuration
AUTH_LDAP_USER_SEARCH = LDAPSearch(
    "ou=Users,dc=company,dc=com",
    ldap.SCOPE_SUBTREE,
    "(sAMAccountName=%(user)s)"  # Use (uid=%(user)s) for some LDAP servers
)

# Attribute mapping from AD to Django user model
AUTH_LDAP_USER_ATTR_MAP = {
    "first_name": "givenName",
    "last_name": "sn",
    "email": "mail",
}

# Always update user attributes on login
AUTH_LDAP_ALWAYS_UPDATE_USER = True
```

#### Step 3: Optional Group-Based Permissions

You can map AD groups to Django permissions:

```python
# Group configuration (optional)
AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
    "ou=Groups,dc=company,dc=com",
    ldap.SCOPE_SUBTREE,
    "(objectClass=group)"
)

AUTH_LDAP_GROUP_TYPE = ActiveDirectoryGroupType()

# User flags mapping based on AD group membership
AUTH_LDAP_USER_FLAGS_BY_GROUP = {
    "is_active": "cn=Active Users,ou=Groups,dc=company,dc=com",
    "is_staff": "cn=Staff,ou=Groups,dc=company,dc=com",
    "is_superuser": "cn=Admins,ou=Groups,dc=company,dc=com"
}

# Cache group memberships for better performance
AUTH_LDAP_CACHE_TIMEOUT = 3600
```

### Testing the Setup

#### Option 1: Test Configuration

Run the built-in configuration test:

```bash
python manage.py test_ad_setup
```

#### Option 2: Test with Real AD User

Test authentication with an actual AD user:

```bash
python manage.py test_ad_setup --test-ad-user --username your-ad-username
```

### Configuration Helper

Use the helper command to generate configuration:

```bash
python manage.py configure_ad --help
```

## Screenshots

![alt text](https://imgur.com/Ah7wPAS.png)

![alt text](https://imgur.com/a6tJoQM.png)

![alt text](https://imgur.com/1Pe0oBo.png)

![alt text](https://imgur.com/8wwEDlQ.png)

![alt text](https://imgur.com/R8CTRyg.png)

![alt text](https://imgur.com/qb0yj3Z.png)


