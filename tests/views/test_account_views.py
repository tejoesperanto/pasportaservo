from datetime import datetime
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings, tag
from django.urls import reverse_lazy

from factory import Faker

from core.utils import join_lazy

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
                    page.response, 'form', 'password1', expected_strings[lang]['field'])
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
                    page.response, 'form', parameter_name, expected_strings[lang])
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
                'eo': "Retpoŝta adreso ne povas komenciĝi per INVALID_ "
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
