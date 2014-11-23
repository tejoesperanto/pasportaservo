try:
    from . import secrets
except ImportError:
    from warnings import warn
    warn("\nFile secrets.py not found.",
    UserWarning)

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

STATIC_URL = 'http://static.pasportaservo.org/'

EMAIL_HOST = secrets.EMAIL_HOST
EMAIL_HOST_USER = secrets.EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = secrets.EMAIL_HOST_PASSWORD
EMAIL_PORT = secrets.EMAIL_PORT
EMAIL_USE_SSL = secrets.EMAIL_USE_SSL
SERVER_EMAIL = secrets.SERVER_EMAIL
DEFAULT_FROM_EMAIL = secrets.DEFAULT_FROM_EMAIL

DEBUG = False

ALLOWED_HOSTS = [
    'pasportaservo.org',
    'www.pasportaservo.org',
    'pasportaservo.batisteo.eu',
]

ADMINS = (
    ('Pasporta Servo', 'saluton@pasportaservo.org'),
    ('Baptiste Darthenay', 'baptiste+pasportaservo3@darthenay.fr'),
)
