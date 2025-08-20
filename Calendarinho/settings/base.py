"""
Base settings for Calendarinho project.
"""
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-default-key-for-development')
AUTH_USER_MODEL = 'users.CustomUser'
LOGIN_URL = '/login/'

# LDAP imports (only imported when needed)
try:
    import ldap
    from django_auth_ldap.config import LDAPSearch, ActiveDirectoryGroupType
    LDAP_AVAILABLE = True
except ImportError:
    LDAP_AVAILABLE = False

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'users.authentication.DualAuthenticationBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Active Directory / LDAP Configuration
# Set to True to enable AD authentication alongside local authentication
ENABLE_AD_AUTHENTICATION = False

# LDAP/AD Server Configuration (configure these when enabling AD)
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

# Always update user on login
AUTH_LDAP_ALWAYS_UPDATE_USER = True

# Find and update groups on every login
AUTH_LDAP_FIND_GROUP_PERMS = True

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

# Enable detailed logging for debugging (optional)
# import logging
# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger('django_auth_ldap')
# logger.addHandler(logging.StreamHandler())
# logger.setLevel(logging.DEBUG)


CRISPY_TEMPLATE_PACK = 'bootstrap4'

#Change to True if you setup SSL certificate (Recommended)
USE_HTTPS = False 

# Domain name to be accessed by users
DOMAIN = "localhost"

# Cost of a working day that was utilized
COST_PER_DAY = 1000

# Weekly working days
WORKING_DAYS = "Mon Tue Wed Thu Sun"

# Alert users before number of days of engagement start date
ALERT_ENG_DAYS = 7

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dal',
    'dal_select2',
    'crispy_forms',
    'crispy_bootstrap4',
    'CalendarinhoApp',
    'users',
    'autocomplete',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Calendarinho.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'CalendarinhoApp.context_processors.alertUpcomingEngagements',
                            'CalendarinhoApp.context_processors.leave_form',
            'CalendarinhoApp.context_processors.engagement_form',
            'CalendarinhoApp.context_processors.client_form',
            'CalendarinhoApp.context_processors.service_form',
            'CalendarinhoApp.context_processors.auth_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'Calendarinho.wsgi.application'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy Forms
CRISPY_TEMPLATE_PACK = 'bootstrap4'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
