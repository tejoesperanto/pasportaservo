from .base import *  # isort:skip

from .sentry import sentry_init

ENVIRONMENT = 'PROD'

SECRET_KEY = get_env_setting('SECRET_KEY')

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'pasportaservo',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': 'unix:/tmp/memcached_prod.sock',
    }
}

EMAIL_BACKEND = "sgbackend.SendGridBackend"
SENDGRID_API_KEY = get_env_setting('SENDGRID_API_KEY')
EMAIL_SUBJECT_PREFIX = '[PS] '
EMAIL_SUBJECT_PREFIX_FULL = '[Pasporta Servo] '

ALLOWED_HOSTS = [
    'pasportaservo.org',
    'www.pasportaservo.org',
]

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')
SECURE_HSTS_SECONDS = 63072000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = 'Strict'

GITHUB_ACCESS_TOKEN = ('Bearer', get_env_setting('GITHUB_ACCESS_TOKEN'))

sentry_init(env=ENVIRONMENT)
