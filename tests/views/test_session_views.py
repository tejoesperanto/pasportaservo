from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import modify_settings, override_settings, tag
from django.urls import reverse_lazy

from django_webtest import WebTest

from ..factories import UserFactory
from .mixins import FormViewTestsMixin
from .pages import LoginPage
from .testcasebase import BasicViewTests


@tag('views', 'views-session', 'views-login')
class LoginViewTests(FormViewTestsMixin, BasicViewTests):
    view_page = LoginPage

    def test_recovery_options(self):
        # The view is expected to provide recovery / reminder options to the
        # user, for the access password and the username.
        test_data = {
            'en': "I forgot my password or my username",
            'eo': "Mi forgesis mian pasvorton aŭ mian salutnomon",
        }
        expected_urls = [reverse_lazy('password_reset'), reverse_lazy('username_remind')]
        for lang in test_data:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                page = self.view_page.open(self, reuse_for_lang=lang)
                recovery_elem = page.get_form_element(".recovery")
                self.assertEqual(recovery_elem.text(), test_data[lang])
                recovery_option_elems = recovery_elem.children("a")
                for i, expected_recovery_option_url in enumerate(expected_urls):
                    with self.subTest(option=recovery_option_elems.eq(i).text()):
                        self.assertEqual(
                            recovery_option_elems.eq(i).attr("href"),
                            expected_recovery_option_url
                        )

    def incorrect_credentials_tests(self, expected_error):
        # The view is expected to show a form error when incorrect credentials
        # (non-existing username / incorrect password for existing username)
        # are supplied.
        # Django mitigates timing-related user enumeration attacks – therefore
        # we don't need to test for that.
        page = self.view_page.open(self)
        for username in (uuid4(), self.user.username):
            with self.subTest(username=username):
                page.submit({
                    'username': username,
                    'password': "wrong-password",
                })
                self.assertEqual(page.response.status_code, 200)
                self.assertTrue('object' in page.form)
                assert 'object' in page.form
                self.assertIsNotNone(page.form['object'])
                assert page.form['object'] is not None
                self.assertGreaterEqual(len(page.form['object'].non_field_errors()), 1)
                self.assertStartsWith(
                    page.form['object'].non_field_errors()[0],
                    expected_error
                )

    def test_incorrect_credentials(self):
        with override_settings(LANGUAGE_CODE='en'):
            # Verify the expected error for incorrect login attempt.
            with self.subTest(lang=settings.LANGUAGE_CODE):
                self.incorrect_credentials_tests(
                    "Please enter the correct username and password.")
        with override_settings(LANGUAGE_CODE='eo'):
            # Verify the correct translation for the incorrect login
            # attempt's expected error.
            with self.subTest(lang=settings.LANGUAGE_CODE):
                self.incorrect_credentials_tests(
                    "Bonvole enigu ĝustajn salutnomon kaj pasvorton.")

    def test_correct_credentials(self):
        test_data = {
            'username': self.user.username,
            'password': "adm1n",
        }

        # The view is expected to redirect to the home page when the correct
        # credentials are supplied.
        page = self.view_page.open(self)
        page.submit(test_data)
        self.assertEqual(page.response.status_code, 302)
        self.assertEqual(page.response.location, '/')
        page.follow()
        # Verify that the user is now authenticated.
        self.assertEqual(page.get_user(), self.user)

        # The view is expected to redirect to the provided destination when
        # the correct credentials are supplied and the next page parameter
        # is included.
        page = self.view_page.open(self)
        page.submit(test_data, redirect_to='/some/where/else/')
        self.assertEqual(page.response.status_code, 302)
        self.assertEqual(page.response.location, '/some/where/else/')

        # Verify fallback support for third-party libraries that do not use
        # the customized next page parameter's name. The view is expected to
        # redirect to the destination provided in the 'next' parameter.
        page = self.view_page.open(self)
        page.submit(test_data | {'next': '/there-and-beyond'})
        self.assertEqual(page.response.status_code, 302)
        self.assertEqual(page.response.location, '/there-and-beyond')

    def test_redirect_if_logged_in(self):
        # The view is expected to redirect to the home page when the user is
        # already authenticated.
        page = self.view_page.open(self, status='*', user=self.user)
        self.assertEqual(page.response.status_code, 302)
        self.assertEqual(page.response.location, '/')

        # The view is expected to redirect to the provided destination when
        # the user is already authenticated and the next page parameter is
        # included.
        page = self.view_page.open(
            self, status='*', user=self.user, redirect_to='/some/where/else/')
        self.assertEqual(page.response.status_code, 302)
        self.assertEqual(page.response.location, '/some/where/else/')

        # Verify fallback support for third-party libraries that do not use
        # the customized next page parameter's name. The view is expected to
        # redirect to the destination provided in the 'next' parameter.
        page = self.view_page.open(
            self, status='*', user=self.user,
            extra_params={'next': '/there-and-beyond'})
        self.assertEqual(page.response.status_code, 302)
        self.assertEqual(page.response.location, '/there-and-beyond')

        # The provided destination is expected to be discarded when it is
        # not within the website.
        page = self.view_page.open(
            self, status='*', user=self.user, redirect_to='https://far.away/')
        self.assertEqual(page.response.status_code, 302)
        self.assertEqual(page.response.location, '/')

    def test_redirect_loop(self):
        base_login_page_url = str(self.url)
        login_page_urls = [
            base_login_page_url.rstrip('/'),
            base_login_page_url + ('/' if base_login_page_url[-1] != '/' else ''),
        ]

        # The view is expected to redirect to the default destination (the
        # home page) when the user is already authenticated and the next page
        # parameter points to the login view.
        for redirect_to in login_page_urls:
            with self.subTest(redirect_url=redirect_to, user="authenticated"):
                with self.assertNotRaises(Exception):
                    self.app.reset()
                    page = self.view_page.open(
                        self, status='*', user=self.user, redirect_to=redirect_to)
                    page.follow()
                self.assertEqual(page.response.status_code, 200)
                self.assertEqual(page.response.request.path, '/')

        # The view is expected to redirect to the default destination (the
        # home page) when an anonymous user successfully authenticates and
        # the next page parameter points to the login view.
        for redirect_to in login_page_urls:
            with self.subTest(redirect_url=redirect_to, user="anonymous"):
                self.app.reset()
                page = self.view_page.open(
                    self, status='*', redirect_to=redirect_to)
                self.assertEqual(page.response.status_code, 200)
                with self.assertNotRaises(Exception):
                    page.submit({
                        'username': self.user.username,
                        'password': "adm1n",
                    })
                    page.follow()
                self.assertEqual(page.response.status_code, 200)
                self.assertEqual(page.response.request.path, '/')

    @override_settings(LANGUAGE_CODE='en')
    def test_user_with_deprecated_hash(self):
        # A user whose password was encoded using an old, now deprecated,
        # hasher is expected to be denied login. Such user should use the
        # password reset option.
        with modify_settings(PASSWORD_HASHERS={
            'prepend': 'django.contrib.auth.hashers.MD5PasswordHasher',
        }):
            user = UserFactory(profile=None, password="madeIn=2009")
        page = self.view_page.open(self)
        page.submit({
            'username': user.username,
            'password': "madeIn=2009",
        })
        self.assertEqual(page.response.status_code, 200)
        self.assertTrue('object' in page.form)
        assert 'object' in page.form
        self.assertIsNotNone(page.form['object'])
        assert page.form['object'] is not None
        self.assertGreaterEqual(len(page.form['object'].non_field_errors()), 1)
        self.assertStartsWith(
            page.form['object'].non_field_errors()[0],
            "Please enter the correct username and password."
        )

    def inactive_user_tests(self, inactive_user, expected_errors):
        # A user who supplied the correct credentials but whose account was
        # deactivated, is expected to see the appropriate notification and
        # to be denied login.
        page = self.view_page.open(self)
        page.submit({
            'username': inactive_user.username,
            'password': "adm1n",
        })
        self.assertEqual(page.response.status_code, 200)
        self.assertTrue('object' in page.form)
        assert 'object' in page.form
        self.assertIsNotNone(page.form['object'])
        assert page.form['object'] is not None
        self.assertLength(page.form['object'].non_field_errors(), 2)
        self.assertEqual(
            page.form['object'].non_field_errors()[0],
            expected_errors[0]
        )
        self.assertStartsWith(
            page.form['object'].non_field_errors()[1],
            expected_errors[1]
        )
        self.assertIn(
            expected_errors[2],
            page.form['object'].non_field_errors()[1]
        )
        notification_link_target = [
            elem.attr("href")
            for elem in page.get_form_element(".alert > a").items()
            if elem.text() == expected_errors[2]
        ]
        self.assertLength(notification_link_target, 1)
        self.assertEqual(notification_link_target[0], reverse_lazy('login_restore'))

    def test_inactive_user(self):
        inactive_user = UserFactory(profile=None, is_active=False)
        with override_settings(LANGUAGE_CODE='en'):
            # Verify the expected errors for the attempt to login with an
            # inactive account.
            with self.subTest(lang=settings.LANGUAGE_CODE):
                self.inactive_user_tests(
                    inactive_user,
                    (
                        "This account is inactive.",
                        "Would you like to re-enable it?",
                        "Inform an administrator.",
                    )
                )
        with override_settings(LANGUAGE_CODE='eo'):
            # Verify the correct translation for the inactive account login
            # attempt's expected errors.
            with self.subTest(lang=settings.LANGUAGE_CODE):
                self.inactive_user_tests(
                    inactive_user,
                    (
                        "Ĉi tiu konto ne estas aktiva.",
                        "Ĉu vi ŝatus ĝin reaktivigi?",
                        "Informi administranton.",
                    )
                )

    def test_custom_cookies(self):
        # When a non-authenticated user accesses the login view,
        # they are expected to have no `seen_at` cookie.
        page = self.view_page.open(self)
        self.assertNotIn('seen_at', self.app.cookies)

        # After successful authentication, the user is expected
        # to be issued with a valid `seen_at` cookie.
        page.submit({
            'username': self.user.username,
            'password': "adm1n",
        })
        cookies = self.app.cookies
        self.assertIn('seen_at', cookies)
        self.assertIsNotNone(cookies['seen_at'])
        assert cookies['seen_at'] is not None
        self.assertTrue(cookies['seen_at'].isdigit())


@tag('views', 'views-session', 'views-logout')
class LogoutViewTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse_lazy('logout')
        cls.user = UserFactory(profile=None)

    def test_view_url(self):
        # Verify that the view can be found at the expected URL.
        response = self.app.get(self.url, status='*')
        self.assertEqual(response.status_code, 302)

        test_data = {
            'en': '/logout/',
            'eo': '/elsaluti/',
        }
        for lang, expected_url in test_data.items():
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang, attempted=expected_url)
            ):
                response = self.app.get(expected_url, status='*')
                self.assertEqual(response.status_code, 302)

    def test_method(self):
        # Verify that logging out via a GET request is possible.
        page = self.app.get(self.url, user=self.user).maybe_follow()
        self.assertTrue('user' in page.context)
        self.assertEqual(page.context['user'], AnonymousUser())

        # Verify that logging out via a POST request is possible.
        page = self.app.get('/', user=self.user)
        page = self.app.post(
            self.url,
            {
                'csrfmiddlewaretoken': page.context['csrf_token'],
            },
            user=self.user)
        page = page.maybe_follow()
        self.assertTrue('user' in page.context)
        self.assertEqual(page.context['user'], AnonymousUser())

    def redirect_tests(self, user):
        # The view is expected to redirect to the home page.
        page = self.app.get(self.url, status=302, user=user)
        self.assertEqual(page.location, '/')

        # The view is expected to redirect to the provided destination when
        # the next page parameter is included.
        self.app.reset()
        page = self.app.get(
            f'{self.url}?{settings.REDIRECT_FIELD_NAME}=/another/page/',
            status=302,
            user=user)
        self.assertEqual(page.location, '/another/page/')

        # The view is expected to ignore the destination provided in the
        # 'next' parameter and redirect to the home page.
        self.app.reset()
        page = self.app.get(
            f'{self.url}?next=/another/page/',
            status=302,
            user=user)
        self.assertEqual(page.location, '/')

        # The provided destination is expected to be discarded when it is
        # not within the website.
        self.app.reset()
        page = self.app.get(
            f'{self.url}?{settings.REDIRECT_FIELD_NAME}=https://far.away/',
            auto_follow=True,
            user=user)
        self.assertEqual(page.request.path, '/')
        self.assertEqual(page.request.server_name, 'testserver')

    def test_redirect_unauthenticated_user(self):
        self.redirect_tests(user=None)

    def test_redirect_logged_in_user(self):
        self.redirect_tests(user=self.user)

    def test_redirect_loop(self):
        base_logout_page_url = str(self.url)
        logout_page_urls = [
            base_logout_page_url.rstrip('/'),
            base_logout_page_url + ('/' if base_logout_page_url[-1] != '/' else ''),
        ]

        # The view is expected to redirect to the default destination (the
        # home page) if the next page parameter points to the logout view and
        # either an authenticated user is logging out or an anonymous user
        # accesses the view.
        for redirect_to in logout_page_urls:
            for user in (self.user, None):
                with self.subTest(
                        redirect_url=redirect_to,
                        user="authenticated" if user else "anonymous",
                ):
                    self.app.reset()
                    page = self.app.get(
                        f'{self.url}?{settings.REDIRECT_FIELD_NAME}={redirect_to}',
                        user=user,
                        auto_follow=True)
                    self.assertEqual(page.status_code, 200)
                    self.assertEqual(page.request.path, '/')

    def test_custom_cookies(self):
        page = self.app.get('/', user=self.user)
        self.assertNotIn('seen_at', self.app.cookies)
        self.app.set_cookie('seen_at', "DUMMY_VALUE")

        # After successful logout, the `seen_at` cookie of the
        # previously authenticated user is expected to be removed.
        page = self.app.post(
            self.url,
            {
                'csrfmiddlewaretoken': page.context['csrf_token'],
            },
            user=self.user)
        self.assertNotIn('seen_at', self.app.cookies)
