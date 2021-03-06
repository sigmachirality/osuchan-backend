"""
Local settings for ...
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Security

# SECURITY WARNING: keep the secret key used in production secret!
# NOTE: use django.core.management.utils.get_random_secret_key() to generate a suitable key
SECRET_KEY = ''

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# NOTE: must not be empty when DEBUG is False
ALLOWED_HOSTS = []

# IPs allowed to use debug toolbar
INTERNAL_IPS = ['127.0.0.1']


# Logging

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'warning.log')
        }
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': True
        }
    }
}


# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': ''
    }
}


# Cache
# https://docs.djangoproject.com/en/dev/ref/settings/#caches

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': ''
    }
}


# Django REST framework
# https://www.django-rest-framework.org/api-guide/settings/

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly'
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        # 'rest_framework.renderers.BrowsableAPIRenderer'
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/minute',
        'user': '45/minute',
        'anon': '1000/day',
        'user': '1500/day'
    }
}


# Celery
# https://docs.celeryproject.org/en/latest/userguide/configuration.html

CELERY_BROKER_URL = "amqp://"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"


# osu! API

# v2
OSU_CLIENT_ID = ''
OSU_CLIENT_SECRET = ''
OSU_CLIENT_REDIRECT_URI = ''

# v1
OSU_API_V1_KEY = ''

# Beatmap cache directory
BEATMAP_CACHE_PATH = ''

# Beta status
BETA = False

# Maintenance status
MAINTENANCE = False
