from uuid import uuid4

from django.conf import settings
from django.test import modify_settings, override_settings, tag
from django.urls import reverse_lazy

from django_webtest import WebTest

from core.forms import UserAuthenticationForm

from ..assertions import AdditionalAsserts
from ..factories import UserFactory


@tag('views', 'views-session', 'views-login')
class LoginViewTests(AdditionalAsserts, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse_lazy('login')
        cls.user = UserFactory(profile=None)

    def test_view_url(self):
        # Verify that the view can be found at the expected URL.
        response = self.app.get(self.url, status='*')
        self.assertEqual(response.status_code, 200)

        test_data = {
            'en': '/login/',
            'eo': '/ensaluti/',
        }
        for lang, expected_url in test_data.items():
            with self.subTest(lang=lang, attempted=expected_url):
                with override_settings(LANGUAGE_CODE=lang):
                    response = self.app.get(expected_url, status='*')
                    self.assertEqual(response.status_code, 200)

    def test_view_title(self):
        # Verify that the view has the expected <title> element.
        test_data = {
            'en': "Log in & Find accommodation | Pasporta Servo",
            'eo': "Ensalutu & Trovu loĝejon | Pasporta Servo",
        }
        for lang in test_data:
            with self.subTest(lang=lang):
                with override_settings(LANGUAGE_CODE=lang):
                    page = self.app.get(self.url, status=200)
                    self.assertHTMLEqual(page.pyquery("title").html(), test_data[lang])

    def test_view_header(self):
        # The view's header is expected to have "login" and "register" links,
        # no username or link to profile, and no use notice.
        test_data = {
            'en': {'session': "log in", 'profile': "register"},
            'eo': {'session': "ensaluti", 'profile': "registriĝi"},
        }
        for lang in test_data:
            with self.subTest(lang=lang):
                with override_settings(LANGUAGE_CODE=lang):
                    page = self.app.get(self.url, status=200)
                    self.assertEqual(
                        page.pyquery("header .nav-session").text(),
                        test_data[lang]['session']
                    )
                    self.assertEqual(
                        page.pyquery("header .nav-profile").text(),
                        test_data[lang]['profile']
                    )
                    self.assertEqual(page.pyquery("header .use-notice").text(), "")

    def test_view_template(self):
        page = self.app.get(self.url, status=200)
        self.assertTemplateUsed(page, 'registration/login.html')

    def test_login_form(self):
        # Verify that the expected form class is in use on the view.
        with override_settings(LANGUAGE_CODE='en'):
            page = self.app.get(self.url, status=200)
        self.assertTrue('form' in page.context)
        self.assertIsInstance(page.context['form'], UserAuthenticationForm)

        # The form is expected to be titled "Log In".
        form_title_selector = ".base-form.login > h4"
        self.assertEqual(page.pyquery(form_title_selector).text(), "Log In")
        with override_settings(LANGUAGE_CODE='eo'):
            page = self.app.get(self.url, status=200)
            self.assertEqual(page.pyquery(form_title_selector).text(), "Ensaluto")

    # TODO: Test "Mi forgesis mian pasvorton aŭ mian salutnomon".

    def incorrect_credentials_tests(self, expected_error):
        # The view is expected to show a form error when incorrect credentials
        # (non-existing username / incorrect password for existing username)
        # are supplied.
        # Django mitigates timing-related user enumeration attacks – therefore
        # we don't need to test for that.
        page = self.app.get(self.url, status=200)
        for username in (uuid4(), self.user.username):
            with self.subTest(username=username):
                page.form['username'] = username
                page.form['password'] = "wrong-password"
                page = page.form.submit()
                self.assertEqual(page.status_code, 200)
                self.assertTrue('form' in page.context)
                self.assertGreaterEqual(len(page.context['form'].non_field_errors()), 1)
                self.assertStartsWith(
                    page.context['form'].non_field_errors()[0],
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
        # The view is expected to redirect to the home page when the correct
        # credentials are supplied.
        page = self.app.get(self.url, status=200)
        test_data = {
            'username': self.user.username,
            'password': "adm1n",
        }
        page = self.app.post(
            self.url,
            {
                **test_data,
                'csrfmiddlewaretoken': page.context['csrf_token'],
            },
            status='*')
        self.assertEqual(page.status_code, 302)
        self.assertEqual(page.location, '/')
        page = page.follow()
        # Verify that the user is now authenticated.
        self.assertTrue('user' in page.context)
        self.assertEqual(page.context['user'], self.user)

        # The view is expected to redirect to the provided destination when
        # the correct credentials are supplied and the next page parameter
        # is included.
        page = self.app.post(
            self.url,
            {
                **test_data,
                'csrfmiddlewaretoken': page.context['csrf_token'],
                settings.REDIRECT_FIELD_NAME: '/some/where/else/',
            },
            status='*')
        self.assertEqual(page.status_code, 302)
        self.assertEqual(page.location, '/some/where/else/')

        # Verify fallback support for third-party libraries that do not use
        # the customized next page parameter's name. The view is expected to
        # redirect to the desitnation provided in the 'next' parameter.
        page = page.follow(status='*')
        page = self.app.post(
            self.url,
            {
                **test_data,
                'csrfmiddlewaretoken': page.context['csrf_token'],
                'next': '/there-and-beyond',
            },
            status='*')
        self.assertEqual(page.status_code, 302)
        self.assertEqual(page.location, '/there-and-beyond')

    def test_redirect_if_logged_in(self):
        # The view is expected to redirect to the home page when the user is
        # already authenticated.
        page = self.app.get(self.url, user=self.user)
        self.assertEqual(page.status_code, 302)
        self.assertEqual(page.location, '/')

        # The view is expected to redirect to the provided destination when
        # the user is already authenticated and the next page parameter is
        # included.
        page = self.app.get(
            f'{self.url}?{settings.REDIRECT_FIELD_NAME}=/some/where/else/',
            user=self.user)
        self.assertEqual(page.status_code, 302)
        self.assertEqual(page.location, '/some/where/else/')

        # Verify fallback support for third-party libraries that do not use
        # the customized next page parameter's name. The view is expected to
        # redirect to the desitnation provided in the 'next' parameter.
        page = self.app.get(
            f'{self.url}?next=/there-and-beyond',
            user=self.user)
        self.assertEqual(page.status_code, 302)
        self.assertEqual(page.location, '/there-and-beyond')

        # The provided destination is expected to be discarded when it is
        # not within the website.
        page = self.app.get(
            f'{self.url}?{settings.REDIRECT_FIELD_NAME}=https://far.away/',
            user=self.user)
        self.assertEqual(page.status_code, 302)
        self.assertEqual(page.location, '/')

    @override_settings(LANGUAGE_CODE='en')
    def test_user_with_deprecated_hash(self):
        # A user whose password was encoded using an old, now deprecated,
        # hasher is expected to be denied login. Such user should use the
        # password reset option.
        with modify_settings(PASSWORD_HASHERS={
            'prepend': 'django.contrib.auth.hashers.MD5PasswordHasher',
        }):
            user = UserFactory(profile=None, password="madeIn=2009")
        page = self.app.get(self.url, status=200)
        page.form['username'] = user.username
        page.form['password'] = "madeIn=2009"
        page = page.form.submit()
        self.assertEqual(page.status_code, 200)
        self.assertTrue('form' in page.context)
        self.assertGreaterEqual(len(page.context['form'].non_field_errors()), 1)
        self.assertStartsWith(
            page.context['form'].non_field_errors()[0],
            "Please enter the correct username and password."
        )

    def inactive_user_tests(self, inactive_user, expected_errors):
        # A user who supplied the correct credentials but whose account was
        # deactivated, is expected to see the appropriate notification and
        # to be denied login.
        page = self.app.get(self.url, status=200)
        page.form['username'] = inactive_user.username
        page.form['password'] = "adm1n"
        page = page.form.submit()
        self.assertEqual(page.status_code, 200)
        self.assertTrue('form' in page.context)
        self.assertEqual(len(page.context['form'].non_field_errors()), 2)
        self.assertEqual(
            page.context['form'].non_field_errors()[0],
            expected_errors[0]
        )
        self.assertStartsWith(
            page.context['form'].non_field_errors()[1],
            expected_errors[1]
        )
        self.assertIn(
            expected_errors[2],
            page.context['form'].non_field_errors()[1]
        )
        # TODO test that warning is logged.
        # TODO the log record should contain the "notification id".
        # TODO test click on "Informi administranton".
        # TODO the new email should contain the "notification id".

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
