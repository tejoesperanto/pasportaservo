from .base import *  # isort:skip


ENVIRONMENT = 'TEST'

SECRET_KEY = 'Saluton Travis!'
DEBUG = True

COMPRESS_OFFLINE = False

EMAIL_SUBJECT_PREFIX = '[PS ci] '
EMAIL_SUBJECT_PREFIX_FULL = '[Pasporta Servo][{}] '.format(ENVIRONMENT)
