from debug_toolbar.panels.request import RequestPanel
from debug_toolbar.panels.logging import LoggingPanel


class CustomRequestPanel(RequestPanel):
    template = 'debug/request_debug.html'

    def generate_stats(self, request, response):
        super().generate_stats(request, response)
        view = (getattr(response, 'context_data', None) or {}).get('view', None)
        auth_stats = {'context_role': {}}
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
        if hasattr(view, 'get_debug_data'):
            auth_stats['context_role'].update({'extra': view.get_debug_data()})
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
        self.record_stats(auth_stats)


class CustomLoggingPanel(LoggingPanel):
    def generate_stats(self, request, response):
        from django.utils import html
        from django.utils.safestring import mark_safe

        super().generate_stats(request, response)
        records = self.get_stats()['records']
        for rec in records:
            msg = html.escape(rec['message']).split('\n')
            msg = "".join(map(
                lambda t: t.replace('\t', "<div style='margin-left:1.5em'>") + "</div>"*t.count('\t'),
                msg))
            rec['message'] = mark_safe(msg)
