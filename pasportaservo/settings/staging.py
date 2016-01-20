from .base import *


SECRET_KEY = get_env_setting('SECRET_KEY')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'staging',
    }
}

EMAIL_HOST = 'mail.gandi.net'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'eraroj@pasportaservo.org'
EMAIL_HOST_PASSWORD = get_env_setting('EMAIL_HOST_PASSWORD')
EMAIL_SUBJECT_PREFIX = '[PS staging] '
DEFAULT_FROM_EMAIL = 'saluton@pasportaservo.org'

ALLOWED_HOSTS = [
    'pasportaservo.me',
    'test.pasportaservo.org',
    'localhost',
]

ADMINS = (
    ('Baptiste Darthenay', 'baptiste.darthenay@gmail.com'),
)
