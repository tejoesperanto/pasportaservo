from django.contrib.sessions.backends.cache import SessionStore
from django.http import HttpRequest
from django.test import override_settings, tag
from django.urls import reverse

from django_webtest import WebTest

from core.forms import UserAuthenticationForm

from ..assertions import AdditionalAsserts
from ..factories import UserFactory


@tag('forms')
@override_settings(LANGUAGE_CODE='en')
class UserAuthenticationFormTests(AdditionalAsserts, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def setUp(self):
        self.dummy_request = HttpRequest()
        session = SessionStore()
        session.create()
        self.dummy_request.session = session

    def test_init(self):
        form_empty = UserAuthenticationForm()
        expected_fields = [
            'username',
            'password',
        ]
        # Verify that the expected fields are part of the form.
        self.assertEquals(set(expected_fields), set(form_empty.fields))

    def test_blank_data(self):
        # Empty form is expected to be invalid.
        form = UserAuthenticationForm(data={})
        self.assertFalse(form.is_valid())

        # Form with empty password field is expected to be invalid.
        form = UserAuthenticationForm(data={'username': self.user.username})
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)

        # Form with empty username field is expected to be invalid.
        form = UserAuthenticationForm(data={'password': "adm1n"})
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    def test_inactive_user_login(self):
        self.user.is_active = False
        self.user.save()

        # The error for an inactive user's login with incorrect credentials is
        # expected to be along the lines of 'incorrect username or password'.
        form = UserAuthenticationForm(
            self.dummy_request, {'username': self.user.username, 'password': "incorrect"})
        self.assertFalse(form.is_valid())
        self.assertStartsWith(
            form.non_field_errors()[0],
            "Please enter the correct username and password")
        self.assertNotIn('restore_request_id', self.dummy_request.session)

        # The error for an inactive user's login with correct credentials is
        # expected to inform that the account is inactive.  In addition, the
        # restore_request_id is expected in the session and a warning emitted
        # on the authentication log.
        with self.assertLogs('PasportaServo.auth', level='WARNING') as log:
            form = UserAuthenticationForm(
                self.dummy_request, {'username': self.user.username, 'password': "adm1n"})
            self.assertFalse(form.is_valid())
        self.assertEqual(form.non_field_errors()[0], str(form.error_messages['inactive']))
        self.assertIn('restore_request_id', self.dummy_request.session)
        self.assertIs(type(self.dummy_request.session['restore_request_id']), tuple)
        self.assertEqual(len(self.dummy_request.session['restore_request_id']), 2)
        self.assertEqual(len(log.records), 1)
        self.assertIn("the account is deactivated", log.output[0])

    def test_active_user_login(self):
        self.assertTrue(self.user.is_active)

        # The error for an active user's login with incorrect credentials is
        # expected to be along the lines of 'incorrect username or password'.
        form = UserAuthenticationForm(
            self.dummy_request, {'username': self.user.username, 'password': "incorrect"})
        self.assertFalse(form.is_valid())
        self.assertStartsWith(
            form.non_field_errors()[0],
            "Please enter the correct username and password")
        self.assertNotIn('restore_request_id', self.dummy_request.session)

        # For an active user's login with correct credentials, no error is
        # expected.  In addition, the restore_request_id shall not be in the
        # session.
        form = UserAuthenticationForm(
            self.dummy_request, {'username': self.user.username, 'password': "adm1n"})
        self.assertTrue(form.is_valid())
        self.assertNotIn('restore_request_id', self.dummy_request.session)

    def test_case_sensitivity(self):
        # The error for login with username different in case is expected to
        # be along the lines of 'incorrect username or password', and inform
        # that the field is case-sensitive.
        for credentials in ((self.user.username.upper(), "incorrect"),
                            (self.user.username.upper(), "adm1n")):
            form = UserAuthenticationForm(
                self.dummy_request, {'username': credentials[0], 'password': credentials[1]})
            self.assertFalse(form.is_valid())
            self.assertStartsWith(
                form.non_field_errors()[0],
                "Please enter the correct username and password")
            self.assertIn("Note that both fields are case-sensitive", form.non_field_errors()[0])

    def test_view_page(self):
        page = self.app.get(reverse('login'))
        self.assertEqual(page.status_int, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertIsInstance(page.context['form'], UserAuthenticationForm)

    def test_form_submit_invalid_credentials(self):
        page = self.app.get(reverse('login'))
        page.form['username'] = "SomeUser"
        page.form['password'] = ".incorrect."
        page = page.form.submit()
        self.assertEqual(page.status_int, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertGreaterEqual(len(page.context['form'].errors), 1)

    def test_form_submit_valid_credentials(self):
        page = self.app.get(reverse('login'))
        page.form['username'] = self.user.username
        page.form['password'] = "adm1n"
        page = page.form.submit()
        self.assertEqual(page.status_int, 302)
        self.assertRedirects(page, '/')
