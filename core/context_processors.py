from django.conf import settings


def expose_selected_settings(request):
    SETTINGS = [
        'ENVIRONMENT',
        'REDIRECT_FIELD_NAME',
        'INVALID_PREFIX',
        'MAPBOX_GL_CSS',
        'MAPBOX_GL_JS',
    ]
    return {name: getattr(settings, name) for name in SETTINGS}
