try:
    from . import secrets
except ImportError:
    from warnings import warn
    warn("\nFile secrets.py not found.",
    UserWarning)

DEBUG = False

SECRET_KEY = secrets.SECRET_KEY

DATABASES = {
    'default': {
        'ENGINE': secrets.DJANGO_DB_ENGINE,
        'NAME': secrets.DJANGO_DB_NAME,
        'USER': secrets.DJANGO_DB_USER,
        'PASSWORD': secrets.DJANGO_DB_PASSWORD,
        'HOST': secrets.DJANGO_DB_HOST,
        'PORT': secrets.DJANGO_DB_PORT,
    }
}

EMAIL_HOST = secrets.EMAIL_HOST
EMAIL_HOST_USER = secrets.EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = secrets.EMAIL_HOST_PASSWORD
EMAIL_PORT = secrets.EMAIL_PORT
EMAIL_USE_SSL = secrets.EMAIL_USE_SSL
SERVER_EMAIL = secrets.SERVER_EMAIL
DEFAULT_FROM_EMAIL = secrets.DEFAULT_FROM_EMAIL

STATIC_URL = 'http://static.pasportaservo.batisteo.eu/'
MEDIA_URL = 'http://static.pasportaservo.batisteo.eu/media/'

ALLOWED_HOSTS = [
    'pasportaservo.batisteo.eu',
]

ADMINS = (
    ('Baptiste Darthenay', 'baptiste+pasportaservo_staging@darthenay.fr'),
)
