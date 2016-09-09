from os import environ, path, listdir


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


from django.conf import global_settings

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/
STATIC_URL = '/static/'
MEDIA_URL = '/media/'

WWW_DIR = path.join(path.dirname(BASE_DIR), 'www')
STATIC_ROOT = path.join(WWW_DIR, 'static')
MEDIA_ROOT = path.join(WWW_DIR, 'media')

STATICFILES_DIRS = (path.join(PROJECT_DIR, 'static'), )

LOCALE_PATHS = (path.join(PROJECT_DIR, 'locale'), )

# Application definition

INSTALLED_APPS = (
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
    'postman',
    'hosting',
    'pages',
    'book',
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

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
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
            ],
        },
    },
]

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

DEFAULT_FROM_EMAIL = 'ne-respondu@pasportaservo.org'



# Non-Django settings:

SITE_NAME = "Pasporta Servo"


# Helps entering phone numbers with "00" instead of "+"
# This means: Interpret phone number as dialed in Poland
PHONENUMBER_DEFAULT_REGION = 'PL'
PHONENUMBER_DEFAULT_FORMAT = 'INTERNATIONAL'


DEFAULT_AVATAR_URL = "mm"


POSTMAN_AUTO_MODERATE_AS = True
POSTMAN_MAILER_APP = None
POSTMAN_SHOW_USER_AS = 'get_full_name'
POSTMAN_DISALLOW_ANONYMOUS = True
POSTMAN_DISALLOW_MULTIRECIPIENTS = True
POSTMAN_DISALLOW_COPIES_ON_REPLY = True
POSTMAN_NOTIFIER_APP = None

OPENCAGE_KEY = 'a27f7e361bdfe11881a987a6e86fb5fd'
