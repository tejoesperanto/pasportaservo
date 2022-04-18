from .base import *  # isort:skip
import os

ENVIRONMENT = 'TEST'

SECRET_KEY = 'Saluton Seninterrompa-Integrado!'
DEBUG = True

COMPRESS_OFFLINE = False

EMAIL_SUBJECT_PREFIX = '[PS ci] '
EMAIL_SUBJECT_PREFIX_FULL = '[Pasporta Servo][{}] '.format(ENVIRONMENT)

DATABASES['default'] = {     # noqa: F405
    **DATABASES['default'],  # noqa: F405
    'USER': os.environ.get('POSTGRES_USERNAME', "pasportaservo"),
    'PASSWORD': os.environ.get('POSTGRES_PASSWORD', "pasportaservo"),
    'HOST': os.environ.get('POSTGRES_HOST', '127.0.0.1'),
    'PORT': os.environ.get('POSTGRES_PORT', '5432'),
}

GITHUB_DISABLE_PREFETCH = True
