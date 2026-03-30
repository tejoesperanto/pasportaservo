from .base import *  # isort:skip

ENVIRONMENT = 'TEST'

SECRET_KEY = '|_|<\\>I+=&=F|_|^/C7I0N4L_~|~3S+§'
DEBUG = False

ALLOWED_HOSTS = [
    'ps-egress.serveousercontent.com',
]
CSRF_TRUSTED_ORIGINS = [
    'https://ps-egress.serveousercontent.com',
]

COMPRESS_ENABLED = False

Q_CLUSTER.update({
    'sync': True,
    'log_level': 'ERROR',
})

for logger_config in LOGGING['loggers'].values():
    if logger_config.get('level') in ('INFO', 'DEBUG'):
        logger_config['level'] = 'ERROR'

WAFFLE_OVERRIDE = True

EMAIL_SUBJECT_PREFIX = '[PS test] '
EMAIL_SUBJECT_PREFIX_FULL = '[Pasporta Servo][{}] '.format(ENVIRONMENT)

GITHUB_DISABLE_PREFETCH = True
