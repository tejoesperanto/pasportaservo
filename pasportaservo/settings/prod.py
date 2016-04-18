from .base import *


SECRET_KEY = get_env_setting('SECRET_KEY')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'pasportaservo',
    }
}

EMAIL_BACKEND = "sgbackend.SendGridBackend"
SENDGRID_API_KEY = get_env_setting('SENDGRID_API_KEY')
EMAIL_SUBJECT_PREFIX = '[PS] '
DEFAULT_FROM_EMAIL = 'ne-respondu@pasportaservo.org'

ALLOWED_HOSTS = [
    'pasportaservo.org',
]

ADMINS = (
    ('Pasporta Servo', 'ne-respondu@pasportaservo.org'),
    ('Baptiste Darthenay', 'baptiste.darthenay@gmail.com'),
)

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
