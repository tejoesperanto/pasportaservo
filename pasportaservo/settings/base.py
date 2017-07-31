from os import environ, path
from django.core.exceptions import ObjectDoesNotExist
from django.conf import global_settings


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

    'django_extensions',
    'django_countries',
    'djangocodemirror',
    'phonenumber_field',
    'bootstrapform',
    'postman',
    'sass_processor',
    'simplemde',
    'solo',

    'core',
    'blog',
    'hosting',
    'links',
    'pages',
    'book',
    'shop',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'dnt.middleware.DoNotTrackMiddleware',
)

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
                'shop.context_processors.reservation',
            ],
        },
    },
]

ROOT_URLCONF = 'pasportaservo.urls'

WSGI_APPLICATION = 'pasportaservo.wsgi.application'

STATICFILES_FINDERS = global_settings.STATICFILES_FINDERS + [
    'sass_processor.finders.CssFinder',
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

AUTH_PROFILE_MODULE = 'hosting.Profile'

LOGIN_URL = 'login'
LOGOUT_URL = '/'
LOGIN_REDIRECT_URL = '/'

REDIRECT_FIELD_NAME = "ps_m"

DEFAULT_FROM_EMAIL = 'Pasporta Servo <saluton@pasportaservo.org>'

CSRF_COOKIE_AGE = None
CSRF_COOKIE_HTTPONLY = True


# Non-Django settings:

COUNTRIES_WITH_REGIONS = ('US', 'GB', 'FR', 'DE', 'BR', 'BE')

# Prefix for marking values (such as email addresses) as no longer valid
# Do not change the value without a data migration!
INVALID_PREFIX = 'INVALID_'


from djangocodemirror.settings import *  # noqa


CORS_ORIGIN_WHITELIST = (
    'pasportaservo.org',
    'localhost:4200',
    'localhost:8000',
)

REST_FRAMEWORK = {
    'PAGE_SIZE': 50,
    'EXCEPTION_HANDLER': 'rest_framework_json_api.exceptions.exception_handler',
    'DEFAULT_PAGINATION_CLASS':
        'rest_framework_json_api.pagination.PageNumberPagination',
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework_json_api.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser'
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework_json_api.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_METADATA_CLASS': 'rest_framework_json_api.metadata.JSONAPIMetadata',
}
JSON_API_FORMAT_KEYS = 'dasherize'

# Helps entering phone numbers with "00" instead of "+"
# This means: Interpret phone number as dialed in Poland
PHONENUMBER_DEFAULT_REGION = 'PL'
PHONENUMBER_DEFAULT_FORMAT = 'INTERNATIONAL'

SOLO_CACHE = 'default'

DEFAULT_AVATAR_URL = "mm"

def user_first_name(user):
    try:
        return user.profile.name
    except ObjectDoesNotExist:
        return user.username

POSTMAN_AUTO_MODERATE_AS = True
POSTMAN_MAILER_APP = None
POSTMAN_SHOW_USER_AS = user_first_name
POSTMAN_DISALLOW_ANONYMOUS = True
POSTMAN_DISALLOW_MULTIRECIPIENTS = True
POSTMAN_DISALLOW_COPIES_ON_REPLY = True
POSTMAN_NOTIFIER_APP = None

OPENCAGE_API_KEY = 'a27f7e361bdfe11881a987a6e86fb5fd'
