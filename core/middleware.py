from hashlib import md5
from typing import cast

from django.conf import settings
from django.contrib.auth.views import (
    LoginView, LogoutView, redirect_to_login as redirect_to_intercept,
)
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest
from django.template.response import TemplateResponse
from django.urls import Resolver404, resolve, reverse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View

import geocoder
import user_agents

from core.models import Agreement, Policy, SiteConfiguration, UserBrowser
from core.views import AgreementRejectView, AgreementView, HomeView
from hosting.models import Preferences, Profile
from hosting.validators import TooNearPastValidator
from pasportaservo.urls import (
    url_index_debug, url_index_maps, url_index_postman,
)


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
            '/fragment/',
            url_index_maps,
        ]
        self.exclude_urls = tuple(str(url) for url in exclude_urls)

    def process_request(self, request):
        if request.path.startswith(self.exclude_urls):
            # Only relevant when using the website itself (not Django-Admin or debug tools),
            # when the file requested is not a static one or a fragment,
            # and when the request is not for resources or configurations related to maps.
            request.skip_hosting_checks = True
            return
        if not request.user.is_authenticated:
            # Only relevant to logged in users.
            return
        profile = Profile.all_objects.filter(user=request.user)[0:1]
        if 'flag_analytics_setup' not in request.session:
            # Update user's analytics consent according to the DNT setting in the browser, first time
            # when the user logs in (DNT==True => opt out). Prior to that the consent is undefined.
            pref = Preferences.objects.filter(profile=profile, site_analytics_consent__isnull=True)
            pref.update(site_analytics_consent=not request.DNT)
            request.session['flag_analytics_setup'] = str(timezone.now())

        self._update_connection_info(request)

        birth_date = profile.values_list('birth_date', flat=True)
        request.user_has_profile = len(birth_date) > 0

        # Is user's age above the legally required minimum?
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
        if trouble_view is not None:
            redirect_response = (
                self._verify_usage_policy_consent(request, trouble_view.func.view_class)
            )
            if redirect_response is not None:
                return redirect_response

        # Is the user trying to use the internal communicator and has a
        # properly configured profile?
        if (request.path.startswith(str(url_index_postman))
                and not request.user_has_profile and not request.user.is_superuser):
            # We can reuse the birth date query result to avoid an additional
            # query in the DB.  For users with a profile, the result will not
            # be empty and hold some value (either datetime or None).
            t = TemplateResponse(
                    request, 'registration/profile_create.html', status=403,
                    context={
                        'function_title': _("Inbox"),
                        'function_description': _(
                            "To be able to communicate with other members of the PS community, "
                            "you need to create a profile."
                        ),
                    })
            t.render()
            return t

    def _verify_usage_policy_consent(self, request: HttpRequest, requested_view: type[View]):
        policy_versions, policies = Policy.objects.all_effective()
        agreement = (
            Agreement.objects
            .filter(
                user=request.user,
                withdrawn__isnull=True,
            )
            .order_by('-created')
            .values_list('policy_version', flat=True)
        )

        if not set(agreement) & set(policy_versions):
            if requested_view != AgreementView:
                return redirect_to_intercept(
                    request.get_full_path(),
                    reverse('agreement'),
                    redirect_field_name=settings.REDIRECT_FIELD_NAME,
                )
            # Policy will be needed to display the Agreement page anyway,
            # so the currently effective policies are immediately fetched
            # from the database.
            current_policy = list(policies)[0] if policies else None
            setattr(request.user, 'consent_required', {
                'given_for': agreement.first(),
                'current': [current_policy],
                'summary': [
                    (p.effective_date, p.changes_summary)
                    for p in policies if p.changes_summary
                ],
            })
            if current_policy is None:
                raise RuntimeError("Service misconfigured: No user agreement was defined.")
        else:
            # Policy most probably will not be needed, so it is lazily
            # evaluated to spare a superfluous query on the database.
            current_policy = policies[0:1]
            policy_summary = SimpleLazyObject(lambda: [  # pragma: no branch
                (p.effective_date, p.changes_summary)
                for p in cast(Policy.objects.__class__, current_policy)
                if p.changes_summary
            ])
            setattr(request.user, 'consent_obtained', {
                'given_for': agreement.first(),
                'current': current_policy,
                'summary': policy_summary,
            })

    def _update_connection_info(self, request: HttpRequest):
        """
        Store information about the browser and device the user is employing and
        where the user is connecting from.
        """
        last_connection_check = request.session.get('flag_connection_logged')
        if last_connection_check is None:
            last_connection_check = timezone.make_aware(timezone.datetime(1887, 1, 1))
        elif isinstance(last_connection_check, str):
            last_connection_check = timezone.datetime.fromisoformat(last_connection_check)
        connection_check = timezone.now() - last_connection_check

        if timezone.timedelta(0) < connection_check < timezone.timedelta(hours=24):
            # Only check once in 24 hours.
            return
        if 'HTTP_USER_AGENT' not in getattr(request, 'META', {}):
            # No information about browser in the request.
            return

        # Decode the UA from the request and retrieve the already known connections
        # of the user with this browser (database records are filtered by UA's hash
        # for quicker comparison).
        ua_string = request.META.get('HTTP_USER_AGENT', '')
        if not isinstance(ua_string, str):
            ua_string = ua_string.decode('utf-8', 'ignore')
        ua_hash = md5(ua_string.encode('utf-8')).hexdigest()
        locations = (
            UserBrowser.objects
            .filter(user=request.user, user_agent_hash=ua_hash)
            .order_by('-pk')
        )
        # Attempt retrieving the user's current geographical location. If it can be
        # found, use it to futher filter the known connections.
        position = geocoder.ip(request.META['HTTP_X_REAL_IP']
                               if settings.ENVIRONMENT not in ('DEV', 'TEST')
                               else "188.166.58.162")
        if position.ok and position.current_result.ok:
            current_location = (f'{position.state}, ' if position.state else '') + position.country
            locations = locations.filter(geolocation=current_location)
        else:
            # When the IPInfo service is unavailable or information about the user's
            # IP cannot be retrieved, we proceed as if the location is unknown.
            current_location = ''
        position.session.close()

        # Verify if the user is connecting with a browser and from a geographical
        # location already known by us.
        connection_data = locations.values_list('pk', 'browser_name').first()
        if connection_data is None:
            # Parse the UA (slow) and create new record only if one does not exist yet.
            ua = user_agents.parse(ua_string)
            conn = UserBrowser(
                user=request.user,
                user_agent_string=ua_string[:250],
                user_agent_hash=ua_hash,
                os_name=ua.os.family[:30],
                os_version=ua.os.version_string[:15],
                browser_name=ua.browser.family[:30],
                browser_version=ua.browser.version_string[:15],
                device_type=ua.get_device()[:30],
                geolocation=current_location,
            )
            conn.save()
            connection_id = conn.pk
            connection_browser = conn.browser_name
        else:
            connection_id, connection_browser = connection_data
        request.session['connection_id'] = connection_id
        request.session['connection_browser'] = connection_browser
        request.session['flag_connection_logged'] = str(timezone.now())
