import time
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import tag
from django.urls import reverse
from django.utils import timezone

from django_webtest import WebTest

from core.models import Policy, UserBrowser

from ..factories import UserFactory


@tag('integration', 'middleware')
class MiddlewareTests(WebTest):
    def test_missing_usage_policies(self):
        Policy.objects.all().delete()
        with self.assertRaisesMessage(
                RuntimeError,
                "Service misconfigured: No user agreement was defined."
        ):
            self.app.get(
                reverse('account_settings'),
                user=UserFactory(profile=None),
                auto_follow=True,
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
        session['flag_connection_logged'] = timezone.now() - timezone.timedelta(hours=25)
        session.save()
        self.app.get(
            self.general_url,
            headers={'User-Agent': 'Mozilla/5.５'.encode('utf-8')})
        mock_geoip.assert_called_once()
        self.assertNotEqual(self.app.session['connection_id'], user_conn_id)
        self.assertEqual(UserBrowser.objects.count(), number_existing_conn_objects + 1)
