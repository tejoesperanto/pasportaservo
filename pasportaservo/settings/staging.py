try:
    import secrets
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
        'PORT': secrets.DJANGO_DB_PORT,
    }
}

STATIC_URL = 'http://static.pasportaservo.org/'
