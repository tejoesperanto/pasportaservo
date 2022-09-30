from django.conf import settings

from debug_toolbar.panels.logging import LoggingPanel
from debug_toolbar.panels.request import RequestPanel


def show_debug_toolbar(request):
    return bool(settings.DEBUG)


class CustomRequestPanel(RequestPanel):
    template = 'debug/request_debug.html'

    def generate_stats(self, request, response):
        super().generate_stats(request, response)
        view = (getattr(response, 'context_data', None) or {}).get('view', None)
        auth_stats = {'context_role': {}}
        if hasattr(view, 'minimum_role'):
            from core.auth import AuthRole
            auth_stats['context_role'].update({
                'role': view.role,
                'role_required':
                    f"= {view.exact_role}" if hasattr(view, 'exact_role')
                    else f">= {view.minimum_role}",
                'is_role_supervisor': view.role >= AuthRole.SUPERVISOR,
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
