from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.mixins import LoginRequiredMixin as AuthenticatedUserRequiredMixin
from django.conf import settings
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
    redirect_field_name = settings.REDIRECT_FIELD_NAME


class UserModifyMixin(object):
    def get_success_url(self, *args, **kwargs):
        try:
            return self.object.profile.get_edit_url()
        except Profile.DoesNotExist:
            return reverse_lazy('profile_create')
