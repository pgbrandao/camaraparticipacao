"""
Django settings for camaraparticipacao project.

Generated by 'django-admin startproject' using Django 3.0.3.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os

from celery.schedules import crontab

import core.tasks

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Base path which will be prepended to all URLs. Should include trailing slash
BASE_PATH = os.environ.get('BASE_PATH', default='/')

LOGIN_URL = BASE_PATH + 'login/'

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', default=False) == 'True'

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS").split(" ")


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'app'
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

ROOT_URLCONF = 'core.urls'
TEMPLATE_DIR = os.path.join(BASE_DIR, "core/templates")  # ROOT dir for templates

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATE_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

STATIC_URL = BASE_PATH + 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'core/static'),
]

DB_DUMP_PATH = '/usr/src/app/db_dump'

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("SQL_ENGINE"),
        "NAME": os.environ.get("SQL_DATABASE"),
        "USER": os.environ.get("SQL_USER"),
        "PASSWORD": os.environ.get("SQL_PASSWORD"),
        "HOST": os.environ.get("SQL_HOST"),
        "PORT": os.environ.get("SQL_PORT"),
    },
}

if "MSSQL_ENQUETES_DATABASE" in os.environ:
    DATABASES["enquetes"] = {
        "ENGINE": os.environ.get("MSSQL_ENGINE"),
        "NAME": os.environ.get("MSSQL_ENQUETES_DATABASE"),
        "USER": os.environ.get("MSSQL_USER"),
        "PASSWORD": os.environ.get("MSSQL_PASSWORD"),
        "HOST": os.environ.get("MSSQL_HOST"),
        "PORT": os.environ.get("MSSQL_PORT"),
        'OPTIONS': {
            'driver': 'ODBC Driver 17 for SQL Server',
            'extra_params': 'Trusted_connection=no'
        },
    }

if "MSSQL_PRISMA_DATABASE" in os.environ:
    DATABASES["prisma"] = {
        "ENGINE": os.environ.get("MSSQL_ENGINE"),
        "NAME": os.environ.get("MSSQL_PRISMA_DATABASE"),
        "USER": os.environ.get("MSSQL_USER"),
        "PASSWORD": os.environ.get("MSSQL_PASSWORD"),
        "HOST": os.environ.get("MSSQL_HOST"),
        "PORT": os.environ.get("MSSQL_PORT"),
        'OPTIONS': {
            'driver': 'ODBC Driver 17 for SQL Server',
            'extra_params': 'Trusted_connection=no'
        },
    }

if "MSSQL_COMENTARIOS_PORTAL_DATABASE" in os.environ:
    DATABASES["comentarios_portal"] = {
        "ENGINE": os.environ.get("MSSQL_ENGINE"),
        "NAME": os.environ.get("MSSQL_COMENTARIOS_PORTAL_DATABASE"),
        "USER": os.environ.get("MSSQL_USER"),
        "PASSWORD": os.environ.get("MSSQL_PASSWORD"),
        "HOST": os.environ.get("MSSQL_HOST"),
        "PORT": os.environ.get("MSSQL_PORT"),
        'OPTIONS': {
            'driver': 'ODBC Driver 17 for SQL Server',
            'extra_params': 'Trusted_connection=no'
        },
    }



# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = False

# import locale
# locale.setlocale(locale.LC_ALL, 'pt_BR')

STRFTIME_SHORT_DATE_FORMAT = '%d/%m/%Y'

ANALYTICS_CREDENTIALS = os.environ['ANALYTICS_CREDENTIALS']

CELERY_BROKER_URL = "redis://redis:6379"
CELERY_RESULT_BACKEND = "redis://redis:6379"

# TODO: This should be configured according to an environment variable
CELERY_BEAT_SCHEDULE = {}

if bool(os.environ.get('AUTO_DATALOADER', default=False)):
    CELERY_BEAT_SCHEDULE["dataloader"] = {
        "task": "core.tasks.dataloader_task",
        "schedule": crontab(hour="5", minute="0"),
    }

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

USE_CACHE = os.environ.get('USE_CACHE', default=False) == 'True'