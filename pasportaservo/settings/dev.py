from .base import *

SECRET_KEY = 'N0_s3kre7~k3Y'
DEBUG = True

INSTALLED_APPS += (
    'debug_toolbar',
)

# MailDump
# $ sudo pip install maildump (python 2 only)
# $ maildump
# http://127.0.0.1:1080/
if DEBUG:
    EMAIL_HOST = '127.0.0.1'
    EMAIL_PORT = '1025'
