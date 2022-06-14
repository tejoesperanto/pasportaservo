from django.conf import settings


def expose_selected_settings(request):
    SETTINGS = [
        'ENVIRONMENT',
        'CURRENT_COMMIT',
        'SUPPORT_EMAIL',
        'REDIRECT_FIELD_NAME',
        'SEARCH_FIELD_NAME',
        'INVALID_PREFIX',
    ]
    context = {name: getattr(settings, name) for name in SETTINGS}
    context.update({'HOUR': 3600})
    return context
