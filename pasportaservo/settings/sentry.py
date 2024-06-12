import re
from typing import TYPE_CHECKING, Optional

from django.urls import reverse

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

if TYPE_CHECKING:
    from sentry_sdk._types import SamplingContext
else:
    SamplingContext = dict

from .base import CURRENT_COMMIT, MEDIA_URL, STATIC_URL, get_env_setting


def sentry_init(env: Optional[str] = None):
    sentry_sdk.init(
        dsn=get_env_setting('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
        environment={'PROD': "production", 'UAT': "staging"}.get(env, "development"),
        release=CURRENT_COMMIT[0] or None,

        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        # send_default_pii=True,

        # Percentage of error events to sample.
        sample_rate=1.0,
        # Percentage of transaction events to sample for performance monitoring.
        traces_sampler=TracesSampler(),
    )


class TracesSampler:
    robot_crawler_re = re.compile(
        r'bot|crawl|spider|slurp|bingpreview|pinterest|mail\.ru'
        + r'|facebookexternalhit|feedfetcher|feedburner',
        re.IGNORECASE
    )
    authenticated_user_cookie_re = re.compile(r'\bseen_at=[A-Za-z0-9]')

    def __call__(self, sampling_context: SamplingContext) -> float:
        if sampling_context['parent_sampled'] is not None:
            return sampling_context['parent_sampled']

        request_info: tuple[str, str] = (
            sampling_context['wsgi_environ'].get('PATH_INFO', ''),
            sampling_context['wsgi_environ'].get('REQUEST_METHOD'),
        )

        bot_match = re.search(
            self.robot_crawler_re,
            sampling_context['wsgi_environ'].get('HTTP_USER_AGENT', ''))
        if (
            bot_match
            or request_info[0].startswith((STATIC_URL, MEDIA_URL))
            or not request_info[0].endswith('/')
        ):
            return 0

        if not hasattr(self, 'paths'):
            self.configure_paths()
        sampling_rate = 0
        reduced_sampling_if_anonymous = False

        match request_info:
            case (path, method) \
                    if path.startswith(self.paths['session']):
                sampling_rate = 0.20 if method == 'POST' else 0.10
            case (path, _) \
                    if path.startswith(self.paths['exploration']):
                sampling_rate = 0.75
                reduced_sampling_if_anonymous = True
            case (path, method) \
                    if path.startswith(self.paths['interesting']):
                sampling_rate = 0.50 if method == 'POST' else 0.40
                reduced_sampling_if_anonymous = True
            case (path, _) \
                    if path.startswith(self.paths['action_link']):
                sampling_rate = 1.00

        if reduced_sampling_if_anonymous and sampling_rate > 0:
            user_match = re.search(
                self.authenticated_user_cookie_re,
                sampling_context['wsgi_environ'].get('HTTP_COOKIE', ''))
            if not user_match:
                sampling_rate *= 0.25

        return sampling_rate

    def trim_path(self, path: str) -> str:
        """
        Returns only the first section (prefix) of the given path.
        """
        base_path = path.lstrip('/').split('/', maxsplit=1)[0]
        return f'/{base_path}/'

    def configure_paths(self):
        from pasportaservo.urls import url_index_maps, url_index_postman

        self.paths = {
            'session': (
                reverse('login'),
                reverse('logout'),
                reverse('register'),
            ),
            'exploration': (
                str(url_index_maps),
                reverse('search'),
            ),
            'interesting': (
                reverse('about'),
                reverse('user_feedback'),
                str(url_index_postman),
                self.trim_path(reverse('place_detail', kwargs={'pk': 0})),
                self.trim_path(reverse('profile_detail', kwargs={'pk': 0, 'slug': "-"})),
                reverse('privacy_policy'),
                reverse('agreement'),
                self.trim_path(reverse('account_settings')),
                # All username-related operations.
                self.trim_path(reverse('username_change')),
                # All password-related operations.
                self.trim_path(reverse('password_change')),
                # All email-related operations.
                self.trim_path(reverse('email_update')),
                # All operations related to confirmation of data.
                self.trim_path(reverse('hosting_info_confirm')),
                reverse('supervisors'),
                reverse('admin:index'),
            ),
            'action_link': (
                self.trim_path(reverse('unique_link', kwargs={'token': '.-'})),
            )
        }
