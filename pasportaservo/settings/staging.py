from .base import *  # isort:skip
from django.contrib.messages import constants as message_level

from .sentry import sentry_init

ENVIRONMENT = 'UAT'

SECRET_KEY = get_env_setting('SECRET_KEY')
MESSAGE_LEVEL = message_level.DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'staging',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': 'unix:/tmp/memcached_staging.sock',
    }
}

EMAIL_BACKEND = 'anymail.backends.postmark.EmailBackend'
POSTMARK_SERVER_TOKEN = get_env_setting('POSTMARK_SERVER_TOKEN')
EMAIL_RICH_ENVELOPES = True
EMAIL_SUBJECT_PREFIX = '[PS ido] '
EMAIL_SUBJECT_PREFIX_FULL = '[Pasporta Servo][{}] '.format(ENVIRONMENT)

ALLOWED_HOSTS = [
    'ido.pasportaservo.org',
    'localhost',
    '127.0.0.1',
]

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

GITHUB_ACCESS_TOKEN = ('Bearer', get_env_setting('GITHUB_ACCESS_TOKEN'))

sentry_init(env=ENVIRONMENT)
