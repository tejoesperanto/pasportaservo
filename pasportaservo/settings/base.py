import locale
from os import environ, path

from django.conf import global_settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext, gettext_lazy


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
COMPRESS_FILTERS = {
    'css': ['compressor.filters.cssmin.CSSCompressorFilter'],
}
COMPRESS_OFFLINE = True
COMPRESS_OFFLINE_MANIFEST = 'static_cache.json'
COMPRESS_OFFLINE_CONTEXT = [
    {},
    # Needed for the extra JS in `place_form` template.
    {'form': {'location': True}},
]

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
    'django.contrib.postgres',
    'django.contrib.gis',

    'fontawesomefree',
    'anymail',
    'compressor',
    'crispy_forms',
    'django_extensions',
    'django_countries',
    'djangocodemirror',
    'djgeojson',
    'el_pagination',
    'logentry_admin',
    'phonenumber_field',
    'postman',
    'sass_processor',
    'simplemde',
    'solo',
    'statici18n',

    'blog',
    'book',
    'chat',
    'core',
    'hosting',
    'links',
    'maps',
    'pages',
    'shop',
)

SHELL_PLUS_DONT_LOAD = [
    'hosting.CountryGroup',
    'hosting.InstanceApprover',
    'hosting.FamilyMemberRepr',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
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
                # 'django.template.context_processors.i18n',
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

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

STATICFILES_FINDERS = global_settings.STATICFILES_FINDERS + [
    'sass_processor.finders.CssFinder',
    'compressor.finders.CompressorFinder',
]
STATICI18N_PACKAGES = ('core', 'hosting', 'pages')
STATICI18N_OUTPUT_DIR = 'js/i18n'

# Database
# https://docs.djangoproject.com/en/stable/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'pasportaservo',
    }
}

# Logging
# https://docs.djangoproject.com/en/stable/topics/logging/#configuring-logging

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins_important_bits': {
            'level': 'WARNING',
            'class': 'django.utils.log.AdminEmailHandler',
        },
        'mail_admins_severe_bits': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        },
    },
    'loggers': {
        'PasportaServo': {
            'handlers': ['mail_admins_severe_bits'],
        },
        'PasportaServo.auth': {
            'handlers': ['mail_admins_important_bits'],
            'propagate': False,
        },
        'PasportaServo.ui': {
            'handlers': ['mail_admins_important_bits'],
        },
    },
}

TEST_EXTERNAL_SERVICES = False

TEST_CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}
TEST_EMAIL_BACKENDS = {
    'dummy': {
        'EMAIL_BACKEND': 'anymail.backends.test.EmailBackend',
        'EMAIL_RICH_ENVELOPES': True,
    },
    'live': {
        'EMAIL_BACKEND': 'anymail.backends.postmark.EmailBackend',
        'POSTMARK_SERVER_TOKEN': 'POSTMARK_API_TEST',
        'EMAIL_RICH_ENVELOPES': True,
    }
}

# Internationalization
# https://docs.djangoproject.com/en/stable/topics/i18n/

LANGUAGE_CODE = 'eo'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Other settings

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
                    for admin in admins.strip('" \t').split(';') if admin)

AUTH_PROFILE_MODULE = 'hosting.Profile'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

REDIRECT_FIELD_NAME = "ps_m"
SEARCH_FIELD_NAME = "ps_q"

DEFAULT_FROM_EMAIL = 'Pasporta Servo <saluton@pasportaservo.org>'
SERVER_EMAIL = 'teknika@pasportaservo.org'

CSRF_COOKIE_AGE = None
CSRF_COOKIE_HTTPONLY = True
SECURE_REFERRER_POLICY = 'origin-when-cross-origin'


# Non-Django settings:

SYSTEM_LOCALE = f'{LANGUAGE_CODE.replace("-", "_")}.{"UTF-8"}'
try:
    locale.setlocale(locale.LC_ALL, SYSTEM_LOCALE)
except locale.Error:
    raise locale.Error(f"Could not set locale {SYSTEM_LOCALE}: make sure that it is enabled on the system.")

def get_current_commit():
    import subprocess
    p = subprocess.run(
        ('git', 'show', '-s', '--no-color', '--format=%h %D'),
        capture_output=True, universal_newlines=True,
    )
    commit_hash, refnames = p.stdout.split(' ', maxsplit=1)
    branch = refnames.strip().replace('HEAD -> ', '').replace('HEAD, ', '').split(',')[0]
    return (commit_hash, branch)

CURRENT_COMMIT = get_current_commit()

# Prefix for marking values (such as email addresses) as no longer valid
# Do not change the value without a data migration!
INVALID_PREFIX = "INVALID_"

# The email address appearing throughout the site which users can contact
# for support or when things go wrong
SUPPORT_EMAIL = "saluton [cxe] pasportaservo.org"


from djangocodemirror.settings import *  # noqa isort:skip

COUNTRIES_OVERRIDE = {
    'GB': {'names': [
        gettext_lazy("Great Britain"),
        gettext_lazy("United Kingdom"),
    ]},
    'FK': {'names': [
        gettext_lazy("Falkland Islands (Malvinas)"),
        gettext_lazy("Islas Malvinas"),
    ]},
    'AS': {'names': [
        gettext_lazy("American Samoa"),
        gettext_lazy("Samoa (Eastern - U.S.)"),
    ]},
}

# Helps entering phone numbers with "00" instead of "+"
# This means: Interpret phone number as dialed in Poland
PHONENUMBER_DEFAULT_REGION = 'PL'
PHONENUMBER_DEFAULT_FORMAT = 'INTERNATIONAL'

SOLO_CACHE = 'default'

DEFAULT_AVATAR_URL = "mm"

EL_PAGINATION_PAGE_LABEL = "p"
EL_PAGINATION_PAGE_OUT_OF_RANGE_404 = True
EL_PAGINATION_ORPHANS = 5

CRISPY_TEMPLATE_PACK = 'bootstrap3'

def user_first_name(user):
    try:
        name = user.profile.name.strip()
        if not name:
            raise ValueError
    except (ObjectDoesNotExist, ValueError):
        return user.username.strip()
    else:
        return name

def postman_from_email(context):
    if context['action'] == 'acceptance':
        sender_name = gettext('{name} via Pasporta Servo')
        user_name = user_first_name(context['object'].sender).capitalize()
        user_name = user_name.translate(str.maketrans({symbol: '_' for symbol in '>@<'}))
        from_sender = f'{sender_name.format(name=user_name)} <saluton@pasportaservo.org>'
    else:
        from_sender = DEFAULT_FROM_EMAIL
    return from_sender

def postman_params_email(context):
    return {
        'headers': {
            # Not supported by SendGrid. Instead, Postman's dynamic from email is used.
            # 'From': postman_from_email(context),
        },
        'reply_to': ['ne-respondu@pasportaservo.org'],
    }

POSTMAN_I18N_URLS = True
POSTMAN_AUTO_MODERATE_AS = True
POSTMAN_MAILER_APP = None
POSTMAN_PARAMS_EMAIL = postman_params_email
POSTMAN_SHOW_USER_AS = user_first_name
POSTMAN_FROM_EMAIL = postman_from_email
POSTMAN_DISALLOW_ANONYMOUS = True
POSTMAN_DISALLOW_MULTIRECIPIENTS = True
POSTMAN_DISALLOW_COPIES_ON_REPLY = True
POSTMAN_NOTIFICATION_APPROVAL = lambda user, *args: not user.email.startswith(INVALID_PREFIX)
POSTMAN_NOTIFIER_APP = None

MAPBOX_GL_BASE_STATIC = 'https://api.tiles.mapbox.com/mapbox-gl-js/v1.13.2/mapbox-gl.{ext}'
MAPBOX_GL_CSS = MAPBOX_GL_BASE_STATIC.format(ext='css')
MAPBOX_GL_CSS_INTEGRITY = 'sha256-c1xXbc3sdLtbVVeTi1PIky7hz+AZfuWd8VMRlfYb7KA='
MAPBOX_GL_JS = MAPBOX_GL_BASE_STATIC.format(ext='js')
MAPBOX_GL_JS_INTEGRITY = 'sha256-JPvw84fpnPKHLBR/JVkIVj11zvi4lYU+Hx0qF+141lo='
del MAPBOX_GL_BASE_STATIC
MAPBOX_GL_RTL_PLUGIN = 'https://api.mapbox.com/mapbox-gl-js/plugins/mapbox-gl-rtl-text/v0.2.3/mapbox-gl-rtl-text.js'

GITHUB_GRAPHQL_HOST = 'https://api.github.com/graphql'
GITHUB_ACCESS_TOKEN = ('Bearer', environ.get('GITHUB_ACCESS_TOKEN', "personal.access.token"))
GITHUB_DISCUSSION_BASE_URL = 'https://github.com/tejoesperanto/pasportaservo/discussions/'
