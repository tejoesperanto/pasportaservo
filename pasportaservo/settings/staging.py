from .base import *
from django.contrib.messages import constants as message_level

SECRET_KEY = get_env_setting('SECRET_KEY')
MESSAGE_LEVEL = message_level.DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'staging',
    }
}

EMAIL_BACKEND = "sgbackend.SendGridBackend"
SENDGRID_API_KEY = get_env_setting('SENDGRID_API_KEY')
EMAIL_SUBJECT_PREFIX = '[PS ido] '

ALLOWED_HOSTS = [
    'ido.pasportaservo.org',
    'localhost',
    '127.0.0.1',
]

ADMINS = (
    ('Baptiste Darthenay', 'baptiste.darthenay@gmail.com'),
)

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
