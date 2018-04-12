from django.conf import settings
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import Resolver404, resolve, reverse
from django.utils.deprecation import MiddlewareMixin
from django.utils.text import format_lazy
from django.utils.translation import ugettext_lazy as _

from core.models import SiteConfiguration
from core.views import HomeView
from hosting.models import Preferences, Profile
from hosting.validators import TooNearPastValidator


class AccountFlagsMiddleware(MiddlewareMixin):
    """
    Updates any flags and settings related to the user's account, whose value
    cannot be pre-determined.
    Checks that pre-conditions for site usage are satisfied.
    """

    def process_request(self, request):
        if not request.user.is_authenticated:
            # Only relevant to logged in users.
            return
        if request.path.startswith(reverse('admin:index')) or request.path.startswith('/__debug__/'):
            # Only relevant when using the website itself (not Django-Admin or debug tools).
            return
        if request.path.startswith(settings.STATIC_URL) or request.path.startswith(settings.MEDIA_URL):
            # Only relevant when the file requested is not a static one.
            return
        profile = Profile.all_objects.filter(user=request.user)[0:1]
        # Update user's analytics consent according to the DNT setting in the browser, first time
        # when the user logs in (DNT==True => opt out). Prior to that the consent is undefined.
        pref = Preferences.objects.filter(profile=profile, site_analytics_consent__isnull=True)
        pref.update(site_analytics_consent=not request.DNT)

        # Is user's age above the legally required minimum?
        birth_date = profile.values_list('birth_date', flat=True)
        trouble_view = None
        try:
            trouble_view = resolve(request.path)
            if trouble_view.func.view_class not in [LoginView, LogoutView, HomeView]:
                try:
                    resolve(request.path, 'pages.urls')
                except Resolver404:
                    # The URL accessed is not one of the general pages.
                    pass
                else:
                    # A general page is ok.
                    trouble_view = None
            else:
                trouble_view = None
        except Resolver404:
            # A non-existent page is ok.
            pass
        if trouble_view is not None and len(birth_date) != 0 and birth_date[0]:
            birth_date = birth_date[0]  # Returned as a list from the query.
            try:
                TooNearPastValidator(SiteConfiguration.USER_MIN_AGE)(birth_date)
            except ValidationError:
                raise PermissionDenied(format_lazy(
                    _("Unfortunately, you are still too young to use Pasporta Servo. "
                      "Wait until you are {min_age} years of age!"),
                    min_age=SiteConfiguration.USER_MIN_AGE
                ))
