from django.views.defaults import permission_denied, ERROR_403_TEMPLATE_NAME
from debug_toolbar.panels.request import RequestPanel


class CustomRequestPanel(RequestPanel):
    template = 'debug/request_debug.html'

    def generate_stats(self, request, response):
        super().generate_stats(request, response)
        view = (getattr(response, 'context_data', None) or {}).get('view', None)
        auth_stats = {'context_role': {}}
        print("=============== Custom Request Debug Panel > START ===============")
        if hasattr(view, 'minimum_role'):
            from core import auth
            auth_roles = auth.ALL_ROLES
            auth_stats['context_role'].update({
                'role': view.role,
                'role_name':
                    next((name for name, val in auth_roles.items() if val == view.role), None),
                'role_required':
                    "= "+str(view.exact_role) if getattr(view, 'exact_role', None) else ">= "+str(view.minimum_role),
                'is_role_supervisor': view.role >= auth.SUPERVISOR,
            })
        if hasattr(request, 'user'):
            from core.auth import PERM_SUPERVISOR
            from hosting.templatetags.profile import supervisor_of
            auth_stats['context_role'].update({
                'is_supervisor': request.user.has_perm(PERM_SUPERVISOR),
                'is_staff': request.user.is_staff,
                'is_admin': request.user.is_superuser,
                'perms':
                    supervisor_of(request.user) if not request.user.is_superuser else ["-- ALL --"],
            })
        print("=============== Custom Request Debug Panel <  END  ===============")
        self.record_stats(auth_stats)


def custom_permission_denied_view(request, exception, template_name=ERROR_403_TEMPLATE_NAME):
    response = permission_denied(request, exception.args[0] if exception.args else exception, template_name)
    try:
        response.context_data = getattr(response, 'context_data', {})
        response.context_data['view'] = exception.args[1]
    except IndexError:
        pass
    return response

