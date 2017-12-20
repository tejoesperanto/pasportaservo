from django.views.defaults import ERROR_403_TEMPLATE_NAME, permission_denied


def custom_permission_denied_view(request, exception, template_name=ERROR_403_TEMPLATE_NAME):
    """
    The Permission Denied view normally lacks information about the view that triggered the
    exception, unless this information was provided in the exception object manually (as the
    second parameter).  This custom view attempts to include the relevant information if it
    is available.
    It is used, among others, by the Auth mixin to provide data about the offending view to
    the Debug toolbar.
    """
    response = permission_denied(request, exception.args[0] if exception.args else exception, template_name)
    try:
        response.context_data = getattr(response, 'context_data', {})
        response.context_data['view'] = exception.args[1]
    except IndexError:
        pass
    return response
