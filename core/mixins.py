from django.conf import settings
from django.contrib.auth.mixins import (
    LoginRequiredMixin as AuthenticatedUserRequiredMixin,
)
from django.urls import reverse_lazy

from hosting.models import Profile


class LoginRequiredMixin(AuthenticatedUserRequiredMixin):
    """
    An own mixin enabling the usage of a custom URL parameter name
    for the redirection after successful authentication. Needed due to
    arbitrary limitations on the parameter name customization by Django.
    """
    redirect_field_name = settings.REDIRECT_FIELD_NAME


class UserModifyMixin(object):
    def get_success_url(self, *args, **kwargs):
        try:
            return self.object.profile.get_edit_url()
        except Profile.DoesNotExist:
            return reverse_lazy('profile_create')


def flatpages_as_templates(cls):
    """
    View decorator:
    Facilitates rendering flat pages as Django templates, including usage of
    tags and the view's context. Performs some magic to capture the specific
    view's custom context and provides a helper function `render_flat_page`.
    """
    context_func_name = 'get_context_data'
    context_func = getattr(cls, context_func_name, None)
    if context_func:
        def _get_context_data_superfunc(self, **kwargs):
            context = context_func(self, **kwargs)
            self._flat_page_context = context
            return context
        setattr(cls, context_func_name, _get_context_data_superfunc)

    def render_flat_page(self, page):
        if not page:
            return ''
        from django.template import engines
        template = engines.all()[0].from_string(page['content'])
        return template.render(
            getattr(self, '_flat_page_context', render_flat_page._view_context),
            self.request)
    cls.render_flat_page = render_flat_page
    cls.render_flat_page._view_context = {}

    return cls
