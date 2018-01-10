from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin

from hosting.models import Preferences, Profile


class AccountFlagsMiddleware(MiddlewareMixin):
    """
    Updates any flags and settings related to the user's account, whose value
    cannot be pre-determined.
    """

    def process_request(self, request):
        if not request.user.is_authenticated:
            # Only relevant to logged in users.
            return
        if request.path.startswith(reverse('admin:index')) or request.path.startswith('/__debug__/'):
            # Only relevant when using the website itself (not Django-Admin or debug tools).
            return
        profile = Profile.all_objects.filter(user=request.user)[0:1]
        # Update user's analytics consent according to the DNT setting in the browser, first time
        # when the user logs in (DNT==True => opt out). Prior to that the consent is undefined.
        pref = Preferences.objects.filter(profile=profile, site_analytics_consent__isnull=True)
        pref.update(site_analytics_consent=not request.DNT)
