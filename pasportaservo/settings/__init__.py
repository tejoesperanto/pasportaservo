"""
Django settings for pasportaservo project.
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
 
from django.conf import global_settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _

def get_env_variable(var_name):
    """ Get the environment variable or return exception """
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = "Set the %s environment variable" % var_name
    raise ImproperlyConfigured(error_msg)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'static/media')

STATICFILES_DIRS = (os.path.join(PROJECT_DIR, 'static'), )

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'hosting/templates'),
    os.path.join(BASE_DIR, 'book/templates'),
    os.path.join(PROJECT_DIR, 'templates'),
)

LOCALE_PATHS = (os.path.join(PROJECT_DIR, 'locale'), )

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/dev/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '*&tc56e)znj!=rpsn1acqp1h#=gesqxj$ezarq05th_6o2=)=b'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = (
    'grappelli',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_extensions',
    'django_countries',
    'phonenumber_field',
    'bootstrapform',
    'leaflet',
    'postman',
    'hosting',
    'pages',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS + (
    'django.core.context_processors.request',
    'postman.context_processors.inbox',
)

ROOT_URLCONF = 'pasportaservo.urls'

WSGI_APPLICATION = 'pasportaservo.wsgi.application'


# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'pasportaservo',
    }
}

# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

LANGUAGE_CODE = 'eo'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


SITE_ID = 1


AUTH_PROFILE_MODULE = 'hosting.Profile'

LOGIN_URL = 'login'
LOGOUT_URL = '/'
LOGIN_REDIRECT_URL = '/'

DEFAULT_FROM_EMAIL = 'nerespondu@pasportaservo.org'



# Non-Django settings:

SITE_NAME = "Pasporta Servo"

GRAPPELLI_ADMIN_TITLE = _("Pasporta Servo administration")


# Helps entering phone numbers with "00" instead of "+"
# This means: Interpret phone number as dialed in Poland
PHONENUMBER_DEFAULT_REGION = 'PL'


DEFAULT_AVATAR_URL = "mm"


LEAFLET_CONFIG = {
    'DEFAULT_CENTER': (40, 0),
    'DEFAULT_ZOOM': 1,
    'MIN_ZOOM': 1,
    'TILES': 'http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    'ATTRIBUTION_PREFIX': 'Mapaj datumoj &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> kontribuantoj',
    'RESET_VIEW': False,
}


POSTMAN_AUTO_MODERATE_AS = True
POSTMAN_MAILER_APP = None
POSTMAN_SHOW_USER_AS = 'get_full_name'
POSTMAN_DISALLOW_ANONYMOUS = True
POSTMAN_DISALLOW_MULTIRECIPIENTS = True
POSTMAN_DISALLOW_COPIES_ON_REPLY = True
POSTMAN_NOTIFIER_APP = None

try:
    from pasportaservo.settings.local_settings import *
except ImportError:
    from warnings import warn
    warn("\nSymbolic link local_settings.py not found. Please create it in the 'settings' folder.",
    UserWarning)

OPENCAGE_KEY = 'a27f7e361bdfe11881a987a6e86fb5fd'
