import time
from typing import NotRequired as NotRequiredDictItem, TypedDict
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import override_settings, tag
from django.urls import reverse
from django.utils import timezone

from django_webtest import WebTest
from faker import Faker
from postman.api import pm_write

from core.models import Policy, UserBrowser
from hosting.models import PasportaServoUser

from .. import DjangoWebtestResponse, UserTag
from ..assertions import AdditionalAsserts
from ..factories import PolicyFactory, UserFactory


@tag('integration', 'middleware')
class MiddlewareTests(AdditionalAsserts, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(profile=None)
        cls.protected_url = reverse('account_settings')

    @override_settings(CACHES=settings.TEST_CACHES)
    def test_missing_usage_policies(self):
        Policy.objects.all().delete()
        with self.assertRaisesMessage(
                RuntimeError,
                "Service misconfigured: No user agreement was defined."
        ):
            self.app.get(
                self.protected_url,
                user=self.user,
                auto_follow=True,
            )

    @override_settings(CACHES=settings.TEST_CACHES)
    def test_redirect_to_agreement(self):
        Policy.objects.all().delete()
        PolicyFactory.create(from_past_date=True, with_summary=False)
        user = UserFactory(profile=None)

        # Accessing a non-general page is expected to be possible when a policy
        # was already accepted by the user.
        page = self.app.get(self.protected_url, user=user, status='*')
        self.assertEqual(page.status_code, 200)

        # A policy becoming effective in the future is not expected to hinder
        # the user, who should still be able to access the non-general page.
        PolicyFactory.create(from_future_date=True, with_summary=False)
        page = self.app.get(self.protected_url, user=user, status='*')
        self.assertEqual(page.status_code, 200)

        # A non-binding policy (requiring no additional agreement from the
        # user) is not expected to hinder that user, who should still be able
        # to access the non-general page.
        PolicyFactory.create(
            effective_date=timezone.now() - timezone.timedelta(days=45),
            with_summary=False, requires_consent=False)
        page = self.app.get(self.protected_url, user=user, status='*')
        self.assertEqual(page.status_code, 200)

        # A new binding policy, which the user is yet to accept, is expected to
        # redirect that user to the agreement screen - instead of the accessed
        # non-general page.
        PolicyFactory.create(
            effective_date=timezone.now() - timezone.timedelta(days=10),
            with_summary=False, requires_consent=True)
        page = self.app.get(self.protected_url, user=user, status='*')
        self.assertEqual(page.status_code, 302)
        self.assertStartsWith(page.location, reverse('agreement'))


@tag('integration', 'middleware')
class PostmanMiddlewareTests(AdditionalAsserts, WebTest):
    csrf_checks = False

    def chat_access_tests(
            self,
            url: str, method: str,
            user: PasportaServoUser, user_tag: UserTag,
            template: str,
            warnings: tuple[str, ...],
    ):
        expected_allowed = user_tag.matches_any('superuser', 'profile:true')
        expected_status = 200 if expected_allowed else 403

        response: DjangoWebtestResponse = (
            getattr(self.app, method)(url, user=user, status='*')
        )
        # Only a user with a profile or an administrator user is expected to be allowed
        # access to the chat endpoints.
        self.assertEqual(response.status_code, expected_status,
                         msg=title.text if (title := response.html.title) else None)
        # The response is expected to be a page indicating the requirement to create a
        # profile, in case the access is disallowed.
        self.assertTemplateUsed(
            response,
            'registration/profile_create.html' if not expected_allowed else template)
        assertion = self.assertNotContains if expected_allowed else self.assertContains
        for warning in warnings:
            assertion(response, warning, status_code=expected_status)

    def test_access_to_chat(self):
        test_users = {
            UserTag('regular', 'profile:false'):
                UserFactory.create(profile=None),
            UserTag('regular', 'profile:true'):
                UserFactory.create(),
            UserTag('staff', 'profile:false'):
                UserFactory.create(is_staff=True, profile=None),
            UserTag('staff', 'profile:true'):
                UserFactory.create(is_staff=True),
            UserTag('superuser', 'profile:false'):
                UserFactory.create(is_superuser=True, profile=None),
        }
        counterparty = UserFactory.create()

        class PageDef(TypedDict):
            view_name: str
            kwargs: NotRequiredDictItem[bool]
            method: str
            template: str
        pages: list[PageDef] = [
            {
                'view_name': 'postman:inbox', 'method': 'get',
                'template': 'postman/inbox.html',
            }, {
                'view_name': 'postman:sent', 'method': 'get',
                'template': 'postman/sent.html',
            }, {
                'view_name': 'postman:write', 'method': 'get',
                'template': 'postman/write.html',
            }, {
                'view_name': 'postman:write', 'method': 'post',
                'template': 'postman/write.html',
            }, {
                'view_name': 'postman:view', 'kwargs': True, 'method': 'get',
                'template': 'postman/view.html',
            }, {
                'view_name': 'postman:reply', 'kwargs': True, 'method': 'get',
                'template': 'postman/reply.html',
            }
        ]
        warning = {
            'en': (
                "Profile required",
                "To be able to communicate with other members of the PS community,"
                " you need to create a profile.",
            ),
            'eo': (
                "Profilo estas necesa",
                "Por havi la eblecon komuniki kun aliaj PS-anoj,"
                " vi devas krei kaj agordi vian profilon.",
            ),
        }

        faker = Faker()
        for user_tag, user in test_users.items():
            for lang in warning:
                for page in pages:
                    with override_settings(LANGUAGE_CODE=lang):
                        message = pm_write(
                            counterparty, user, faker.sentence(), faker.paragraph())
                        url = reverse(
                            page['view_name'],
                            kwargs={'message_id': message.pk} if page.get('kwargs') else {})
                        with self.subTest(
                                user=user_tag,
                                url=f"{page['method'].upper()} {url}",
                                lang=lang,
                        ):
                            self.chat_access_tests(
                                url, page['method'], user, user_tag,
                                page['template'], warning[lang],
                            )


@tag('integration', 'middleware')
class ConnectionInfoTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(profile=None)
        cls.general_url = reverse('about')

    def test_anonymous_user(self):
        self.app.get(self.general_url, user=AnonymousUser())
        self.assertNotIn('connection_id', self.app.session, msg=self.app.session.items())
        self.assertNotIn('connection_browser', self.app.session, msg=self.app.session.items())

    def test_missing_user_agent_info(self):
        self.app.get(self.general_url, user=self.user)
        self.assertNotIn('connection_id', self.app.session, msg=self.app.session.items())
        self.assertNotIn('connection_browser', self.app.session, msg=self.app.session.items())

    @patch('core.middleware.geocoder.ip')
    def test_connection_logged(self, mock_geoip):
        number_existing_conn_objects = UserBrowser.objects.count()
        mock_geoip.return_value.ok = mock_geoip.return_value.current_result.ok = True

        # Accessing the website from a browser (that sends a user agent string)
        # is expected to log a new connection.
        mock_geoip.return_value.state = None
        mock_geoip.return_value.country = 'AQ'
        self.app.get(
            self.general_url,
            user=self.user,
            headers={'User-Agent': 'Mozilla/5.0'})
        mock_geoip.assert_called_once()
        self.assertIn('connection_id', self.app.session, msg=self.app.session.items())
        user_conn_id = self.app.session['connection_id']
        self.assertIn('connection_browser', self.app.session, msg=self.app.session.items())
        self.assertEqual(self.app.session['connection_browser'], "Other")
        self.assertEqual(UserBrowser.objects.count(), number_existing_conn_objects + 1)

        self.app.reset()
        mock_geoip.reset_mock()

        # Accessing the website from the same browser and a different location
        # is expected to log a new connection.
        mock_geoip.return_value.state = None
        mock_geoip.return_value.country = 'GL'
        self.app.get(
            self.general_url,
            user=self.user,
            headers={'User-Agent': 'Mozilla/5.0'})
        mock_geoip.assert_called_once()
        self.assertIn('connection_id', self.app.session, msg=self.app.session.items())
        self.assertNotEqual(self.app.session['connection_id'], user_conn_id)
        self.assertIn('connection_browser', self.app.session, msg=self.app.session.items())
        self.assertEqual(self.app.session['connection_browser'], "Other")
        self.assertEqual(UserBrowser.objects.count(), number_existing_conn_objects + 2)

    @patch('core.middleware.geocoder.ip')
    def test_connection_not_logged(self, mock_geoip):
        mock_geoip.return_value.ok = mock_geoip.return_value.current_result.ok = True
        mock_geoip.return_value.state = 'Saskatchewan'
        mock_geoip.return_value.country = 'CA'
        self.app.get(
            self.general_url,
            user=self.user,
            headers={'User-Agent': 'Mozilla/5.0'})
        user_conn_id = self.app.session['connection_id']
        number_existing_conn_objects = UserBrowser.objects.count()

        self.app.reset()
        mock_geoip.reset_mock()

        # Accessing the website from the same browser and location is not expected
        # to log a new connection.
        self.app.get(
            self.general_url,
            user=self.user,
            headers={'User-Agent': 'Mozilla/5.0'})
        mock_geoip.assert_called_once()
        self.assertIn('connection_id', self.app.session, msg=self.app.session.items())
        self.assertEqual(self.app.session['connection_id'], user_conn_id)
        self.assertEqual(UserBrowser.objects.count(), number_existing_conn_objects)

        self.app.reset()
        mock_geoip.reset_mock()

        # Accessing the website from the same browser and an unknown location is
        # not expected to log a new connection.
        mock_geoip.return_value.current_result.ok = False
        self.app.get(
            self.general_url,
            user=self.user,
            headers={'User-Agent': 'Mozilla/5.0'})
        mock_geoip.assert_called_once()
        self.assertIn('connection_id', self.app.session, msg=self.app.session.items())
        self.assertEqual(self.app.session['connection_id'], user_conn_id)
        self.assertEqual(UserBrowser.objects.count(), number_existing_conn_objects)

    @patch('core.middleware.geocoder.ip')
    def test_connection_reuse(self, mock_geoip):
        mock_geoip.return_value.ok = mock_geoip.return_value.current_result.ok = False
        self.app.get(
            self.general_url,
            user=self.user,
            headers={'User-Agent': 'Mozilla/5.0'})
        user_conn_id = self.app.session['connection_id']
        number_existing_conn_objects = UserBrowser.objects.count()

        mock_geoip.reset_mock()
        time.sleep(0.250)

        # Accessing the website again in a short period of time through the
        # same session, even if the browser and/or the location differ, is
        # expected to reuse the existing connection.
        mock_geoip.return_value.ok = mock_geoip.return_value.current_result.ok = True
        mock_geoip.return_value.state = 'Nunavut'
        mock_geoip.return_value.country = 'CA'
        self.app.get(
            self.general_url,
            headers={'User-Agent': 'Mozilla/5.５'.encode('utf-8')})
        mock_geoip.assert_not_called()
        self.assertEqual(self.app.session['connection_id'], user_conn_id)
        self.assertEqual(UserBrowser.objects.count(), number_existing_conn_objects)

        mock_geoip.reset_mock()

        # Accessing the website again after more than 24 hours through the
        # same session is expected to log a new connection.
        session = self.app.session
        session['flag_connection_logged'] = str(timezone.now() - timezone.timedelta(hours=25))
        session.save()
        self.app.get(
            self.general_url,
            headers={'User-Agent': 'Mozilla/5.５'.encode('utf-8')})
        mock_geoip.assert_called_once()
        self.assertNotEqual(self.app.session['connection_id'], user_conn_id)
        self.assertEqual(UserBrowser.objects.count(), number_existing_conn_objects + 1)
