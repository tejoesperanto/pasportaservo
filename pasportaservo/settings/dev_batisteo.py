from debug_toolbar import settings as dt_settings

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

    'debug_toolbar',
)

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

dt_settings.CONFIG_DEFAULTS['JQUERY_URL'] = "/static/js/jquery.min.js"
