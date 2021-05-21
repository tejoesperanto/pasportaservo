from django.conf import settings
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.views import redirect_to_login as redirect_to_intercept
from django.core.exceptions import PermissionDenied, ValidationError
from django.template.response import TemplateResponse
from django.urls import Resolver404, resolve, reverse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.utils.text import format_lazy
from django.utils.translation import ugettext_lazy as _

from core.models import Agreement, Policy, SiteConfiguration
from core.views import AgreementRejectView, AgreementView, HomeView
from hosting.models import Preferences, Profile
from hosting.validators import TooNearPastValidator
from pasportaservo.urls import url_index_debug, url_index_maps, url_index_postman


class AccountFlagsMiddleware(MiddlewareMixin):
    """
    Updates any flags and settings related to the user's account, whose value
    cannot be pre-determined.
    Checks that pre-conditions for site usage are satisfied.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        exclude_urls = [
            reverse('admin:index'),
            url_index_debug,
            settings.STATIC_URL,
            settings.MEDIA_URL,
            '/favicon.ico',
            url_index_maps,
        ]
        self.exclude_urls = tuple(str(url) for url in exclude_urls)

    def process_request(self, request):
        if not request.user.is_authenticated:
            # Only relevant to logged in users.
            return
        if request.path.startswith(self.exclude_urls):
            # Only relevant when using the website itself (not Django-Admin or debug tools),
            # when the file requested is not a static one,
            # and when the request is not for resources or configurations related to maps.
            request.skip_hosting_checks = True
            return
        profile = Profile.all_objects.filter(user=request.user)[0:1]
        if 'flag_analytics_setup' not in request.session:
            # Update user's analytics consent according to the DNT setting in the browser, first time
            # when the user logs in (DNT==True => opt out). Prior to that the consent is undefined.
            pref = Preferences.objects.filter(profile=profile, site_analytics_consent__isnull=True)
            pref.update(site_analytics_consent=not request.DNT)
            request.session['flag_analytics_setup'] = str(timezone.now())

        # Is user's age above the legally required minimum?
        birth_date = profile.values_list('birth_date', flat=True)
        trouble_view = None
        try:
            trouble_view = resolve(request.path)
            if (hasattr(trouble_view.func, 'view_class') and trouble_view.func.view_class not in
                    [LoginView, LogoutView, HomeView, AgreementRejectView]):
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
            birth_date_value = birth_date[0]  # Returned as a list from the query.
            try:
                TooNearPastValidator(SiteConfiguration.USER_MIN_AGE)(birth_date_value)
            except ValidationError:
                raise PermissionDenied(format_lazy(
                    _("Unfortunately, you are still too young to use Pasporta Servo. "
                      "Wait until you are {min_age} years of age!"),
                    min_age=SiteConfiguration.USER_MIN_AGE
                ))

        # Has the user consented to the most up-to-date usage policy?
        policy = (Policy.objects.order_by('-id').values('version', 'content'))[0:1]
        if trouble_view is not None:
            agreement = Agreement.objects.filter(
                user=request.user, policy_version__in=policy.values_list('version'), withdrawn__isnull=True)
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

        if request.path.startswith(url_index_postman) and len(birth_date) == 0 and not request.user.is_superuser:
            # We can reuse the birth date query result to avoid an additional
            # query in the DB.  For users with a profile, the result will not
            # be empty and hold some value (either datetime or None).
            t = TemplateResponse(
                    request, 'registration/profile_create.html', status=403,
                    context={
                        'function_title': _("Inbox"),
                        'function_description': _("To be able to communicate with other members of the PS community, "
                                                  "you need to create a profile."),
                    })
            t.render()
            return t
