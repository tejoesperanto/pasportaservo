from os import environ, path

from django.conf import global_settings
from django.core.exceptions import ObjectDoesNotExist


def get_env_setting(setting):
    """ Get the environment setting or return exception """
    from django.core.exceptions import ImproperlyConfigured
    try:
        return environ[setting]
    except KeyError:
        error_msg = "Set the %s environment variable" % setting
        raise ImproperlyConfigured(error_msg)


PROJECT_DIR = path.dirname(path.dirname(path.abspath(__file__)))
BASE_DIR = path.dirname(PROJECT_DIR)


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/

STATIC_URL = '/static/'
MEDIA_URL = '/media/'

WWW_DIR = path.join(path.dirname(BASE_DIR), 'www')
STATIC_ROOT = path.join(WWW_DIR, 'static')
MEDIA_ROOT = path.join(WWW_DIR, 'media')

STATICFILES_DIRS = (path.join(PROJECT_DIR, 'static'), )

LOCALE_PATHS = (path.join(BASE_DIR, 'locale'), )

SASS_PRECISION = 8
SASS_PROCESSOR_INCLUDE_DIRS = [
    path.join(BASE_DIR, 'core/static/sass'),
]

COMPRESS_OUTPUT_DIR = ''
COMPRESS_REBUILD_TIMEOUT = 31536000
COMPRESS_CSS_FILTERS = [
    'compressor.filters.cssmin.CSSCompressorFilter',
]
COMPRESS_OFFLINE = True
COMPRESS_OFFLINE_MANIFEST = 'static_cache.json'

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.flatpages',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',

    'compressor',
    'django_extensions',
    'django_countries',
    'djangocodemirror',
    'djgeojson',
    'logentry_admin',
    'phonenumber_field',
    'bootstrapform',
    'postman',
    'sass_processor',
    'simplemde',
    'solo',

    'blog',
    'book',
    'core',
    'hosting',
    'links',
    'maps',
    'pages',
    'shop',
)

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'dnt.middleware.DoNotTrackMiddleware',
    'core.middleware.AccountFlagsMiddleware',
]

AUTHENTICATION_BACKENDS = ['core.auth.SupervisorAuthBackend']

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            path.join(BASE_DIR, 'core/templates'),
            path.join(BASE_DIR, 'hosting/templates'),
            path.join(PROJECT_DIR, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                'postman.context_processors.inbox',
                'core.context_processors.expose_selected_settings',
                'shop.context_processors.reservation_check',
            ],
        },
    },
]

ROOT_URLCONF = 'pasportaservo.urls'

WSGI_APPLICATION = 'pasportaservo.wsgi.application'

STATICFILES_FINDERS = global_settings.STATICFILES_FINDERS + [
    'sass_processor.finders.CssFinder',
    'compressor.finders.CompressorFinder',
]

# Database
# https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
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

ADMINS = (
    ('Pasporta Servo', 'saluton@pasportaservo.org'),
)
try:
    admins = environ['PS_ADMINS']
except KeyError:
    pass
else:
    cleanup = lambda name, address: (name.lstrip('§').strip(), address)
    ADMINS += tuple(cleanup(*('§ ' + admin).rsplit(maxsplit=1))
                    for admin in admins.strip().split(';') if admin)

AUTH_PROFILE_MODULE = 'hosting.Profile'

LOGIN_URL = 'login'
LOGOUT_URL = '/'
LOGIN_REDIRECT_URL = '/'

REDIRECT_FIELD_NAME = "ps_m"

DEFAULT_FROM_EMAIL = 'Pasporta Servo <saluton@pasportaservo.org>'

CSRF_COOKIE_AGE = None
CSRF_COOKIE_HTTPONLY = True


# Non-Django settings:


# Prefix for marking values (such as email addresses) as no longer valid
# Do not change the value without a data migration!
INVALID_PREFIX = "INVALID_"


from djangocodemirror.settings import *                                         # noqa  isort:skip

# Helps entering phone numbers with "00" instead of "+"
# This means: Interpret phone number as dialed in Poland
PHONENUMBER_DEFAULT_REGION = 'PL'
PHONENUMBER_DEFAULT_FORMAT = 'INTERNATIONAL'

SOLO_CACHE = 'default'

DEFAULT_AVATAR_URL = "mm"

def user_first_name(user):
    try:
        name = user.profile.name
        if not name:
            raise ValueError
        return name
    except (ObjectDoesNotExist, ValueError):
        return user.username

POSTMAN_I18N_URLS = True
POSTMAN_AUTO_MODERATE_AS = True
POSTMAN_MAILER_APP = None
POSTMAN_SHOW_USER_AS = user_first_name
POSTMAN_DISALLOW_ANONYMOUS = True
POSTMAN_DISALLOW_MULTIRECIPIENTS = True
POSTMAN_DISALLOW_COPIES_ON_REPLY = True
POSTMAN_NOTIFIER_APP = None

MAPBOX_GL_BASE_STATIC = 'https://api.tiles.mapbox.com/mapbox-gl-js/v0.49.0/mapbox-gl.{ext}'
MAPBOX_GL_CSS = MAPBOX_GL_BASE_STATIC.format(ext='css')
MAPBOX_GL_JS = MAPBOX_GL_BASE_STATIC.format(ext='js')
MAPBOX_GL_RTL_PLUGIN = 'https://api.mapbox.com/mapbox-gl-js/plugins/mapbox-gl-rtl-text/v0.1.2/mapbox-gl-rtl-text.js'
