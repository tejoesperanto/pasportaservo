from django.conf import settings


def some_settings(request):
    SETTINGS = [
        'INVALID_PREFIX',
    ]
    return {name: getattr(settings, name) for name in SETTINGS}
