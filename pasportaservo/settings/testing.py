from .base import *  # isort:skip
import os

ENVIRONMENT = 'TEST'

SECRET_KEY = 'Saluton Seninterrompa-Integrado!'
DEBUG = True

COMPRESS_OFFLINE = False

Q_CLUSTER.update({
    'sync': True,
    'log_level': 'ERROR',
})

for logger_config in LOGGING['loggers'].values():
    if logger_config.get('level') in ('INFO', 'DEBUG'):
        logger_config['level'] = 'ERROR'

WAFFLE_OVERRIDE = True

EMAIL_SUBJECT_PREFIX = '[PS ci] '
EMAIL_SUBJECT_PREFIX_FULL = '[Pasporta Servo][{}] '.format(ENVIRONMENT)

DATABASES['default'] = {
    **DATABASES['default'],
    'USER': os.environ.get('POSTGRES_USERNAME', "pasportaservo"),
    'PASSWORD': os.environ.get('POSTGRES_PASSWORD', "pasportaservo"),
    'HOST': os.environ.get('POSTGRES_HOST', '127.0.0.1'),
    'PORT': os.environ.get('POSTGRES_PORT', '5432'),
}

GITHUB_DISABLE_PREFETCH = True
