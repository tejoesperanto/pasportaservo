from .base import *


SECRET_KEY = get_env_setting('SECRET_KEY')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'staging',
    }
}

EMAIL_BACKEND = "sgbackend.SendGridBackend"
SENDGRID_API_KEY = get_env_setting('SENDGRID_API_KEY')
EMAIL_SUBJECT_PREFIX = '[PS staging] '
DEFAULT_FROM_EMAIL = 'ne-respondu@pasportaservo.org'

ALLOWED_HOSTS = [
    'test.pasportaservo.org',
    'localhost',
    '127.0.0.1',
]

ADMINS = (
    ('Baptiste Darthenay', 'baptiste.darthenay@gmail.com'),
)
