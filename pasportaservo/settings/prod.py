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
GOOGLE_ANALYTICS_KEY = 'UA-99737795-1'
EMAIL_SUBJECT_PREFIX = '[PS] '

ALLOWED_HOSTS = [
    'pasportaservo.org',
]

ADMINS = (
    ('Pasporta Servo', 'saluton@pasportaservo.org'),
    ('Baptiste Darthenay', 'baptiste.darthenay@gmail.com'),
)

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
