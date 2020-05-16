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
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

sentry_init(env=ENVIRONMENT)
