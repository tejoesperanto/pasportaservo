from .base import *

SECRET_KEY = 'N0_s3kre7~k3Y'
DEBUG = True
TEMPLATE_DEBUG = DEBUG

INSTALLED_APPS += (
    'debug_toolbar',
)

EMAIL_BACKEND = "sgbackend.SendGridBackend"
SENDGRID_API_KEY = "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"
