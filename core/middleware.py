from django.conf import settings
from django.contrib.auth.views import (
    LoginView, LogoutView, redirect_to_login as redirect_to_intercept,
)
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import Resolver404, resolve, reverse
from django.utils.deprecation import MiddlewareMixin
from django.utils.text import format_lazy
from django.utils.translation import ugettext_lazy as _

from core.models import Agreement, Policy, SiteConfiguration
from core.views import AgreementRejectView, AgreementView, HomeView
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
            request.skip_hosting_checks = True
            return
        if request.path.startswith(settings.STATIC_URL) or request.path.startswith(settings.MEDIA_URL):
            # Only relevant when the file requested is not a static one.
            request.skip_hosting_checks = True
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
            if trouble_view.func.view_class not in [LoginView, LogoutView, HomeView, AgreementRejectView]:
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

        # Has the user consented to the most up-to-date usage policy?
        policy = (Policy.objects.order_by('-id').values('version', 'content'))[0:1]
        # TODO: temporary fallback, when flat pages are available again remove
        #       this (id's should be extracted from flat pages only).
        from django.template.loader import get_template

        class MonkeyDict(dict):
            def values_list(self, param):
                return self[param]

            def first(self):
                if not getattr(self, 'parsed', False):
                    self['content'] = get_template(self['content']).template.source
                self.parsed = True
                return self

            def __getitem__(self, index):
                if index == 0:
                    return self.first()
                else:
                    return super().__getitem__(index)

        policy = MonkeyDict(
            version='2018-001',
            content='pages/snippets/privacy_policy_initial.html',
        )
        # ENDTODO
        if trouble_view is not None:
            agreement = Agreement.objects.filter(
                user=request.user, policy_version=policy.values_list('version'), withdrawn__isnull=True)
            if not agreement.exists():
                # Policy will be needed to display the following page anyway,
                # so it is immediately fetched from the database.
                request.user.consent_required = [policy.first()]
                if request.user.consent_required[0] is None:
                    raise RuntimeError("Service misconfigured: No user agreement was defined.")
                if trouble_view.func.view_class != AgreementView:
                    return redirect_to_intercept(
                        request.get_full_path(),
                        reverse('agreement'),
                        redirect_field_name=settings.REDIRECT_FIELD_NAME
                    )
            else:
                # Policy most probably will not be needed, so it is lazily
                # evaluated to spare a superfluous query on the database.
                request.user.consent_obtained = policy
