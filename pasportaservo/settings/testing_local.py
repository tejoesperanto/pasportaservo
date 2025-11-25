from .base import *  # isort:skip

ENVIRONMENT = 'TEST'

SECRET_KEY = '|_|<\\>I+=&=F|_|^/C7I0N4L_~|~3S+§'
DEBUG = False

COMPRESS_ENABLED = False

EMAIL_SUBJECT_PREFIX = '[PS test] '
EMAIL_SUBJECT_PREFIX_FULL = '[Pasporta Servo][{}] '.format(ENVIRONMENT)

GITHUB_DISABLE_PREFETCH = True
