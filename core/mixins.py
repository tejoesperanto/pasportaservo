from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.mixins import LoginRequiredMixin as AuthenticatedUserRequiredMixin
from django.conf import settings
from django.urls import reverse_lazy
from django.utils.functional import keep_lazy_text
from django.utils.translation import ugettext_lazy as _
from django.utils.text import format_lazy

from django_countries.fields import Country

from hosting.models import Profile


class SupervisorRequiredMixin(UserPassesTestMixin):
    raise_exception = True
    permission_denied_message = _("Only the supervisors of {this_country} can access this page")

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        try:
            return self.request.user.profile.is_supervisor_of(countries=[self.country])
        except AttributeError:
            return self.request.user.profile.is_supervisor_of(self.user.profile)
        except Profile.DoesNotExist:
            return False

    def get_permission_denied_message(self):
        try:
            countries = [self.country]
        except AttributeError:
            countries = set(self.user.profile.owned_places.filter(
                available=True, deleted=False).values_list('country', flat=True))
            if not countries:
                return _("Only administrators can access this page")
        to_string = lambda item: str(Country(item).name)
        join_lazy = keep_lazy_text(lambda items: ", ".join(map(to_string, items)))
        return format_lazy(self.permission_denied_message, this_country=join_lazy(countries))


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
            # Avoid polluting the namespace of the view class.
            cls.render_flat_page._view_context = context
            return context
        setattr(cls, context_func_name, _get_context_data_superfunc)

    def render_flat_page(self, page):
        if not page:
            return ''
        from django.template import engines
        template = engines.all()[0].from_string(page['content'])
        return template.render(render_flat_page._view_context, self.request)
    cls.render_flat_page = render_flat_page
    cls.render_flat_page._view_context = {}

    return cls
