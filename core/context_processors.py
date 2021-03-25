from django.conf import settings


def expose_selected_settings(request):
    SETTINGS = [
        'ENVIRONMENT',
        'CURRENT_COMMIT',
        'SUPPORT_EMAIL',
        'REDIRECT_FIELD_NAME',
        'INVALID_PREFIX',
        'MAPBOX_GL_CSS',
        'MAPBOX_GL_CSS_INTEGRITY',
        'MAPBOX_GL_JS',
        'MAPBOX_GL_JS_INTEGRITY',
    ]
    context = {name: getattr(settings, name) for name in SETTINGS}
    context.update({'HOUR': 3600})
    return context
