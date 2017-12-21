from .base import *  # isort:skip
import logging

from django.contrib.messages import constants as message_level

from debug_toolbar.settings import PANELS_DEFAULTS as DEBUG_PANEL_DEFAULTS

SECRET_KEY = 'N0_s3kre7~k3Y'
DEBUG = True
MESSAGE_LEVEL = message_level.DEBUG

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
]


logging.getLogger('PasportaServo.auth').setLevel(logging.INFO)

SASS_PROCESSOR_ROOT = path.join(BASE_DIR, 'core', 'static')

INSTALLED_APPS += (
    'debug_toolbar',
)

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

DEBUG_TOOLBAR_CONFIG = {
    # 'JQUERY_URL': '',
    'JQUERY_URL': '/static/js/jquery.min.js',
    # Disable the Templates panel that freaks out in Django 1.11
    'DISABLE_PANELS': {
        'debug_toolbar.panels.redirects.RedirectsPanel',
        'debug_toolbar.panels.templates.TemplatesPanel',
    },
}

DEBUG_TOOLBAR_PANELS = DEBUG_PANEL_DEFAULTS[:]
DEBUG_TOOLBAR_PANELS[
    DEBUG_TOOLBAR_PANELS.index('debug_toolbar.panels.request.RequestPanel')
    ] = 'pasportaservo.debug.CustomRequestPanel'
DEBUG_TOOLBAR_PANELS.remove(
    'debug_toolbar.panels.logging.LoggingPanel')
DEBUG_TOOLBAR_PANELS.insert(
    DEBUG_TOOLBAR_PANELS.index('debug_toolbar.panels.sql.SQLPanel')+1,
    'pasportaservo.debug.CustomLoggingPanel')


# MailDump
# $ sudo pip install maildump (python 2 only)
# $ maildump
# http://127.0.0.1:1080/
if DEBUG:
    EMAIL_HOST = '127.0.0.1'
    EMAIL_PORT = '1025'
    INTERNAL_IPS = ('127.0.0.1',)
