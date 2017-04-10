from django.conf import settings


def expose_selected_settings(request):
    SETTINGS = [
        'INVALID_PREFIX',
    ]
    return {name: getattr(settings, name) for name in SETTINGS}
