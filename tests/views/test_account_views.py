import itertools
from collections import namedtuple
from datetime import datetime, timedelta
from importlib import import_module
from typing import cast
from unittest.mock import patch

from django.conf import settings
from django.contrib.sessions.backends.base import SessionBase
from django.core import mail
from django.test import override_settings, tag
from django.urls import reverse_lazy

from django_webtest import WebTest
from django_webtest.response import DjangoWebtestResponse
from factory import Faker

from core.utils import join_lazy

from ..assertions import AdditionalAsserts
from ..factories import UserFactory
from .mixins import FormViewTestsMixin
from .pages import RegisterPage
from .testcasebase import BasicViewTests


def _snake_str(string: str) -> str:
    return ''.join([c.lower() if i % 2 else c.upper() for i, c in enumerate(string)])


@tag('views', 'views-account', 'views-register')
class RegisterViewTests(FormViewTestsMixin, BasicViewTests):
    view_page = RegisterPage

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.faker = Faker._get_faker()

    def test_redirect_if_logged_in(self):
        for user_tag in self.users:
            if user_tag == 'basic':
                expected_url = {
                    'en': ('/profile/create/', ''),
                    'eo': ('/profilo/krei/', '')
                }
            else:
                expected_url = {
                    'en': (f'/profile/{self.users[user_tag].profile.pk}/', '/edit/'),
                    'eo': (f'/profilo/{self.users[user_tag].profile.pk}/', '/aktualigi/'),
                }
            for lang in expected_url:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(user=user_tag, lang=lang)
                ):
                    # The view is expected to redirect to the user's profile editing or
                    # creation page when the user is already authenticated.
                    page = self.view_page.open(self, status='*', user=self.users[user_tag])
                    self.assertEqual(page.response.status_code, 302)
                    self.assertStartsWith(page.response.location, expected_url[lang][0])
                    self.assertEndsWith(page.response.location, expected_url[lang][1])

                    # The view is expected to redirect to the provided destination when
                    # the user is already authenticated and the next page parameter is
                    # included.
                    page = self.view_page.open(
                        self, redirect_to='/somewhere/else/', status='*', user=self.users[user_tag])
                    self.assertEqual(page.response.status_code, 302)
                    self.assertEqual(page.response.location, '/somewhere/else/')

                    # The provided destination is expected to be discarded when it is
                    # not within the website.
                    page = self.view_page.open(
                        self, redirect_to='https://faraway/', status='*', user=self.users[user_tag])
                    self.assertEqual(page.response.status_code, 302)
                    self.assertStartsWith(page.response.location, expected_url[lang][0])

    def _prepare_registration_values(self, **pre_set_values):
        password_value = self.faker.password()
        return {
            'username': f'{self.faker.user_name()}_{datetime.now().timestamp()}',
            'password1': password_value,
            'password2': password_value,
            'email': self.faker.email(),
            **pre_set_values,
        }

    @patch('core.mixins.is_password_compromised')
    def test_correct_details(self, mock_pwd_check):
        # When all provided details are valid, the view is expected to redirect
        # the user to the profile creation page and log them in automatically.
        mock_pwd_check.return_value = (False, 0)
        expected_next_step = {
            'en': ('/profile/create/', "You are logged in."),
            'eo': ('/profilo/krei/', "Vi nun estas ensalutinta."),
        }

        for lang in expected_next_step:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                page = self.view_page.open(self)
                test_data = self._prepare_registration_values(**{
                    settings.REDIRECT_FIELD_NAME: '/go-nowhere/',
                })
                mock_pwd_check.reset_mock()
                page.submit(test_data)
                self.assertEqual(page.response.status_code, 302)
                # The value of the redirection parameter is expected to be ignored.
                self.assertEqual(page.response.location, expected_next_step[lang][0])
                mock_pwd_check.assert_called_once_with(test_data['password1'])
                page.follow()
                # The user is expected to be logged in now.
                user = page.get_user()
                self.assertIsNotNone(user)
                self.assertIsNotNone(user.pk)
                self.assertEqual(user.username, test_data['username'])
                # A top-level login success message is expected to be displayed to
                # the user.
                messages = page.get_toplevel_messages()
                self.assertIn(expected_next_step[lang][1], messages['content'])
                self.assertEqual(
                    messages['level'][messages['content'].index(expected_next_step[lang][1])],
                    'success'
                )

    @patch('core.mixins.is_password_compromised')
    def test_weak_password_error_and_hint(self, mock_pwd_check):
        # The view is expected to show a hint about choosing a strong password
        # to the user, when an overly weak password is typed.
        mock_pwd_check.return_value = (True, 250)
        expected_strings = {
            'en': {
                'form': "The password selected by you is too insecure.",
                'field': "Choose a less easily guessable password.",
                'hint': "How to choose a good password?",
            },
            'eo': {
                'form': "La pasvorto elektita de vi estas tro nesekura.",
                'field': "Bonvole elektu pli malfacile diveneblan pasvorton.",
                'hint': "Kiel elekti bonan pasvorton?",
            },
        }
        expected_url = join_lazy('#', (reverse_lazy('faq'), 'kiel-elekti-bonan-pasvorton'))

        for lang in expected_strings:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                page = self.view_page.open(self)
                test_data = self._prepare_registration_values()
                mock_pwd_check.reset_mock()
                page.submit(test_data)
                self.assertEqual(page.response.status_code, 200)
                mock_pwd_check.assert_called_once_with(test_data['password1'])
                self.assertStartsWith(page.get_form_errors(), expected_strings[lang]['form'])
                self.assertFormError(
                    page.response.context['form'], 'password1',
                    expected_strings[lang]['field'])
                self.assertEqual(
                    page.get_form_errors('password1'),
                    [expected_strings[lang]['field']])
                hint_elem = page.get_form_element(".password-hint")
                self.assertEqual(hint_elem.text(), expected_strings[lang]['hint'])
                hint_link = hint_elem.children("a")
                self.assertLength(hint_link, 1)
                self.assertEqual(hint_link.attr("href"), expected_url)

    @patch('core.mixins.is_password_compromised')
    def invalid_parameter_value_tests(
            self, parameter_name, parameter_value, expected_strings, mock_pwd_check,
    ):
        # When some provided detail is invalid, an error is expected to be
        # shown for the relevant form field upon the frm submission.
        mock_pwd_check.return_value = (False, 0)
        for lang in expected_strings:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                page = self.view_page.open(self)
                test_data = self._prepare_registration_values(**{
                    parameter_name: parameter_value,
                })
                page.submit(test_data)
                self.assertEqual(page.response.status_code, 200)
                mock_pwd_check.assert_called_with(test_data['password1'])
                self.assertFormError(
                    page.response.context['form'], parameter_name,
                    expected_strings[lang]
                )
                self.assertEqual(
                    page.get_form_errors(parameter_name),
                    [expected_strings[lang]]
                )

    def test_existing_username_error(self):
        self.invalid_parameter_value_tests(
            'username', _snake_str(self.user.username),
            {
                'en': "A user with a similar username already exists.",
                'eo': "Uzanto kun simila salutnomo jam ekzistas.",
            },
        )

    def test_existing_email_error(self):
        self.invalid_parameter_value_tests(
            'email', _snake_str(self.user.email),
            {
                'en': "User address already in use.",
                'eo': "Adreso de uzanto jam utiligita ĉe la retejo.",
            },
        )

    def test_invalid_email_error(self):
        self.invalid_parameter_value_tests(
            'email', f'{settings.INVALID_PREFIX}{self.faker.email()}',
            {
                'en': "Email address cannot start with INVALID_ "
                      + "(in all-capital letters).",
                'eo': "Retpoŝta adreso ne povas komenciĝi per ‘INVALID_’ "
                      + "(per ĉiuj majusklaj literoj).",
            },
        )

    def test_incongruent_passwords_error(self):
        self.invalid_parameter_value_tests(
            'password2', ")AbCdEf(",
            {
                'en': "The two password fields didn’t match.",
                'eo': "La du pasvortaj kampoj ne kongruas.",
            },
        )

    # TODO: Integration test for the honeypot.
    # TODO: Integration test for the complete registration flow.


@tag('views', 'views-account')
class AccountRestoreRequestViewTests(AdditionalAsserts, WebTest):
    # Related validations are also performed by Form tests for UserAuthenticationForm
    # and by the functional tests for the login process.

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.SessionStore = cast(
            type[SessionBase],
            import_module(settings.SESSION_ENGINE).SessionStore)

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse_lazy('login_restore')

    def setUp(self):
        self.session = cast(SessionBase, self.app.session or self.SessionStore())
        self.session.cycle_key()
        self.session_header = {
            'Cookie': f'{settings.SESSION_COOKIE_NAME}={self.session.session_key}',
        }

    def test_redirect_authenticated_user(self):
        TestData = namedtuple('TestData', 'timestamp, redirect, user_tag')
        test_dataset = itertools.product(
            (None, datetime.now().timestamp()),
            (None, '/another/page/', 'https://far.away/'),
            ('basic', 'regular'),
        )
        users = {
            'basic': UserFactory.create(profile=None),
            'regular': UserFactory.create(),
        }

        for test_data in test_dataset:
            test_data = TestData(*test_data)
            internal_redirect = test_data.redirect and test_data.redirect.startswith('/')
            with self.subTest(
                    user=test_data.user_tag,
                    timestamp=test_data.timestamp,
                    next=(('internal' if internal_redirect else 'external')
                          if test_data.redirect else False),
            ):
                # Initialize the logged-in user's session by requesting an unrelated page.
                self.app.get('/', user=users[test_data.user_tag])
                session = cast(SessionBase, self.app.session)
                if test_data.timestamp is not None:
                    session['restore_request_id'] = ("QWERTY", test_data.timestamp)
                else:
                    session['restore_request_id'] = None
                    del session['restore_request_id']
                session.save()
                redirect_param = (
                    f'?{settings.REDIRECT_FIELD_NAME}={test_data.redirect}'
                    if test_data.redirect
                    else '')

                response: DjangoWebtestResponse = self.app.get(
                    f'{self.url}{redirect_param}', status=302)
                # The view is expected to redirect a logged-in user:
                # * If a valid redirection destination is specified in the request,
                #   to that destination.
                # * If the redirection destination is invalid or not specified,
                #   - to the user's profile when set up
                #   - to the home page when the user has no profile yet.
                if internal_redirect:
                    expected_location = test_data.redirect
                elif test_data.user_tag == 'regular':
                    expected_location = users[test_data.user_tag].profile.get_absolute_url()
                else:
                    expected_location = '/'
                self.assertEqual(response.location, expected_location)
                # No email is expected to be sent by the view.
                self.assertLength(mail.outbox, 0)

                page = response.follow(status='*')
                # No notification is expected to be shown to the logged-in user.
                self.assertLength(page.context.get('messages', []), 0)
                self.assertLength(page.pyquery("section.messages .message"), 0)

    def test_redirect_missing_or_invalid_restore_request(self):
        TestData = namedtuple('TestData', 'timestamp, redirect, expect_message')
        test_dataset = [
            TestData(None, None, False),
            TestData(None, '/another/page/', False),
            TestData(None, 'https://far.away/', False),
            TestData("0", None, False),
            TestData("0", '/some/where/else/', False),
            TestData((datetime.now() - timedelta(minutes=90)).timestamp(), None, True),
            TestData((datetime.now() - timedelta(hours=2)).timestamp(), '/not/here', True),
        ]
        expected_location = reverse_lazy('login')
        expected_message = {
            'en': "Something misfunctioned. Please log in again and retry.",
            'eo': "Io misfunkciis. Bonvole ensalutu denove kaj reprovu.",
        }

        for test_data in test_dataset:
            for lang in expected_message:
                with (
                    override_settings(LANGUAGE_CODE=lang),
                    self.subTest(
                        lang=lang,
                        timestamp=test_data.timestamp,
                        next=bool(test_data.redirect),
                    )
                ):
                    if test_data.timestamp is not None:
                        self.session['restore_request_id'] = ("QWERTY", test_data.timestamp)
                    else:
                        self.session['restore_request_id'] = None
                        del self.session['restore_request_id']
                    self.session.save()
                    redirect_param = (
                        f'?{settings.REDIRECT_FIELD_NAME}={test_data.redirect}'
                        if test_data.redirect
                        else '')

                    response: DjangoWebtestResponse = self.app.get(
                        f'{self.url}{redirect_param}', status=302, headers=self.session_header)
                    # The view is expected to redirect to the login page.
                    self.assertEqual(response.location, expected_location)
                    # The view is expected to prevent caching by the browser.
                    self.assertIsNotNone(response.cache_control.no_cache)
                    # No email is expected to be sent by the view.
                    self.assertLength(mail.outbox, 0)

                    page = response.follow()
                    pyquery = page.pyquery
                    if not test_data.expect_message:
                        # No notification is expected to be shown to the user in case of
                        # missing or invalid restore request.
                        self.assertLength(page.context.get('messages', []), 0)
                        self.assertLength(pyquery("section.messages .message"), 0)
                    else:
                        # In case of an expired restore request, a notification is expected
                        # to be shown to the user.
                        self.assertLength(page.context.get('messages', []), 1)
                        self.assertEqual(
                            pyquery("section.messages .message [id^='MSG_']").text(),
                            expected_message[lang])
                    # The login form is expected to display no error.
                    self.assertLength(pyquery(".base-form .alert"), 0)

    def test_valid_restore_request(self):
        expected_messages = {
            'en': {
                'admin': "Note to admin",
                'user': "OK : An administrator will contact you soon.",
            },
            'eo': {
                'admin': "Sciigo al admino",
                'user': "Enordas : Administranto baldaŭ kontaktiĝos kun vi.",
            },
        }

        for lang in expected_messages:
            with (
                override_settings(LANGUAGE_CODE=lang),
                self.subTest(lang=lang)
            ):
                self.session['restore_request_id'] = (
                    "ABC-DEF-GHIJ", (datetime.now() - timedelta(minutes=15)).timestamp(),
                )
                self.session.save()
                mail.outbox = []

                page = self.app.get(self.url, status='*', headers=self.session_header)
                pyquery = page.pyquery
                self.assertEqual(page.status_code, 200)
                # An email is expected to be sent by the view to the administrators,
                # specifying the ID of the restore request.
                self.assertEqual(len(mail.outbox), 1)
                self.assertIn(expected_messages[lang]['admin'], mail.outbox[0].subject)
                self.assertIn("ABC-DEF-GHIJ", mail.outbox[0].subject)
                # The user is expected to be shown a success result message that the
                # administrators were notified.
                self.assertEqual(
                    pyquery("#subtitle").text(),
                    expected_messages[lang]['user'])
                # No (further) notification is expected to be displayed to the user.
                self.assertLength(page.context.get('messages', []), 0)
                self.assertLength(pyquery("section.messages .message"), 0)
