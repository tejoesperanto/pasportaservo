from .base import *  # isort:skip
import logging
import socket

from django.contrib.messages import constants as message_level

from debug_toolbar.settings import PANELS_DEFAULTS as DEBUG_PANEL_DEFAULTS

ENVIRONMENT = 'DEV'

SECRET_KEY = 'N0_s3kre7~k3Y'
DEBUG = True
MESSAGE_LEVEL = message_level.DEBUG

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
]
try:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(('10.0.0.10', 0))
        ALLOWED_HOSTS.append(s.getsockname()[0])
except (OSError, IndexError):
    pass


logging.getLogger('PasportaServo.auth').setLevel(logging.INFO)
logging.getLogger('PasportaServo.geo').setLevel(logging.DEBUG)

SASS_PROCESSOR_ROOT = path.join(BASE_DIR, 'core', 'static')

CRISPY_FAIL_SILENTLY = False

INSTALLED_APPS += (
    'debug_toolbar',
)

MIDDLEWARE.insert(
    [i for i, mw in enumerate(MIDDLEWARE) if mw.startswith('django')][-1] + 1,
    'debug_toolbar.middleware.DebugToolbarMiddleware'
)

DEBUG_TOOLBAR_CONFIG = {
    'JQUERY_URL': '/static/js/jquery.min.js',
    'DISABLE_PANELS': {
        'debug_toolbar.panels.redirects.RedirectsPanel',
    },
    'SHOW_TOOLBAR_CALLBACK': 'pasportaservo.debug.show_debug_toolbar',
}

DEBUG_TOOLBAR_PANELS = DEBUG_PANEL_DEFAULTS[:]
DEBUG_TOOLBAR_PANELS[
    DEBUG_TOOLBAR_PANELS.index('debug_toolbar.panels.request.RequestPanel')
    ] = 'pasportaservo.debug.CustomRequestPanel'
DEBUG_TOOLBAR_PANELS.remove(
    'debug_toolbar.panels.logging.LoggingPanel')
DEBUG_TOOLBAR_PANELS.insert(
    DEBUG_TOOLBAR_PANELS.index('debug_toolbar.panels.sql.SQLPanel') + 1,
    'pasportaservo.debug.CustomLoggingPanel')


# MailDump
# $ sudo pip install maildump (python 2 only)
# $ maildump
# http://127.0.0.1:1080/
if DEBUG:
    EMAIL_HOST = '127.0.0.1'
    EMAIL_PORT = '1025'
    INTERNAL_IPS = ('127.0.0.1',)
ANYMAIL_DEBUG_API_REQUESTS = True

EMAIL_SUBJECT_PREFIX = '[PS test] '
EMAIL_SUBJECT_PREFIX_FULL = '[Pasporta Servo][{}] '.format(ENVIRONMENT)


GITHUB_DISABLE_PREFETCH = True
