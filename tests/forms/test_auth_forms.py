from django.conf import settings
from django.contrib.sessions.backends.cache import SessionStore
from django.core import mail
from django.http import HttpRequest
from django.test import override_settings, tag
from django.urls import reverse

from django_webtest import WebTest

from core.forms import (
    EmailStaffUpdateForm, EmailUpdateForm,
    UserAuthenticationForm, UsernameUpdateForm,
)

from ..assertions import AdditionalAsserts
from ..factories import UserFactory


def _snake_str(string):
    return ''.join([c if i % 2 else c.upper() for i, c in enumerate(string)])


@tag('forms', 'forms-auth')
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
        self.user.refresh_from_db()

    def test_init(self):
        form_empty = UserAuthenticationForm()
        expected_fields = [
            'username',
            'password',
        ]
        # Verify that the expected fields are part of the form.
        self.assertEqual(set(expected_fields), set(form_empty.fields))

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


@tag('forms', 'forms-auth')
@override_settings(LANGUAGE_CODE='en')
class UsernameUpdateFormTests(AdditionalAsserts, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def setUp(self):
        self.user.refresh_from_db()

    def test_init(self):
        form = UsernameUpdateForm(instance=self.user)
        # Verify that the expected fields are part of the form.
        self.assertEqual(['username'], list(form.fields))
        # Verify that the form stores the username before a change.
        self.assertTrue(hasattr(form, 'previous_uname'))
        self.assertEqual(form.previous_uname, self.user.username)
        # Verify the form's save method is protected in templates.
        self.assertTrue(
            hasattr(form.save, 'alters_data')
            or hasattr(form.save, 'do_not_call_in_templates')
        )

    def test_blank_data(self):
        # Empty form is expected to be invalid.
        form = UsernameUpdateForm(data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'username': ["This field is required."]})

    def test_invalid_username(self):
        test_data = [
            (
                # Too-long username is expected to be rejected.
                "a" * (self.user._meta.get_field('username').max_length + 1),
                f"Ensure that this value has at most "
                f"{self.user._meta.get_field('username').max_length} characters"
            ),
            # Username consisting of only whitespace is expected to be rejected.
            (" \t \r \f ", "This field is required"),
            # Usernames containing invalid characters are expected to be rejected.
            (self.user.username + " id", "Enter a username conforming to these rules: "),
            (self.user.username + "=+~", "Enter a username conforming to these rules: "),
            ("A<B", "Enter a username conforming to these rules: "),
        ]
        for new_username, expected_error in test_data:
            with self.subTest(value=new_username):
                form = UsernameUpdateForm(data={'username': new_username}, instance=self.user)
                self.assertFalse(form.is_valid())
                self.assertEqual(len(form.errors['username']), 1)
                self.assertStartsWith(form.errors['username'][0], expected_error)

    def test_same_username(self):
        # Username without any change is expected to be accepted.
        form = UsernameUpdateForm(data={'username': self.user.username}, instance=self.user)
        self.assertTrue(form.is_valid())

        UserFactory(username=_snake_str(self.user.username))
        form = UsernameUpdateForm(data={'username': self.user.username}, instance=self.user)
        self.assertTrue(form.is_valid())

    def test_case_modified_username(self):
        form = UsernameUpdateForm(
            data={'username': self.user.username.capitalize()},
            instance=self.user)
        self.assertTrue(form.is_valid())
        form = UsernameUpdateForm(
            data={'username': self.user.username.upper()},
            instance=self.user)
        self.assertTrue(form.is_valid())

    def test_case_modified_nonunique_username(self):
        UserFactory(username=_snake_str(self.user.username))
        UserFactory(username=self.user.username.upper())
        form = UsernameUpdateForm(
            data={'username': self.user.username.capitalize()},
            instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {'username': ["A user with a similar username already exists."]}
        )

    def test_nonunique_username(self):
        other_user = UserFactory()
        for new_username in (other_user.username,
                             other_user.username.capitalize(),
                             _snake_str(other_user.username)):
            with self.subTest(value=new_username):
                form = UsernameUpdateForm(data={'username': new_username}, instance=self.user)
                self.assertFalse(form.is_valid())
                self.assertEqual(
                    form.errors,
                    {'username': ["A user with a similar username already exists."]}
                )

    def test_valid_data(self):
        new_username = self.user.username * 2
        form = UsernameUpdateForm(data={'username': new_username}, instance=self.user)
        self.assertTrue(form.is_valid())
        user = form.save(commit=False)
        self.assertEqual(user.pk, self.user.pk)
        self.assertEqual(user.username, new_username)

    def test_view_page(self):
        page = self.app.get(reverse('username_change'), user=self.user)
        self.assertEqual(page.status_int, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertIsInstance(page.context['form'], UsernameUpdateForm)

    def test_form_submit(self):
        page = self.app.get(reverse('username_change'), user=self.user)
        page.form['username'] = new_username = _snake_str(self.user.username)
        page = page.form.submit()
        self.user.refresh_from_db()
        self.assertRedirects(
            page,
            reverse('profile_edit', kwargs={
                'pk': self.user.profile.pk,
                'slug': self.user.profile.autoslug})
        )
        self.assertEqual(self.user.username, new_username)


@tag('forms', 'forms-auth')
@override_settings(LANGUAGE_CODE='en')
class EmailUpdateFormTests(AdditionalAsserts, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.invalid_email_user = UserFactory(invalid_email=True)

    def setUp(self):
        self.user.refresh_from_db()
        self.invalid_email_user.refresh_from_db()

    def _init_form(self, data=None, instance=None):
        return EmailUpdateForm(data=data, instance=instance)

    def test_init(self):
        form = self._init_form(instance=self.user)
        # Verify that the expected fields are part of the form.
        self.assertEqual(['email'], list(form.fields))
        # Verify that the form stores the email address before a change.
        self.assertTrue(hasattr(form, 'previous_email'))
        self.assertEqual(form.previous_email, self.user.email)
        self.assertEqual(form.initial['email'], form.previous_email)

        form = self._init_form(instance=self.invalid_email_user)
        # Verify that the form stores the cleaned up email address.
        self.assertTrue(hasattr(form, 'previous_email'))
        self.assertEqual(form.previous_email, self.invalid_email_user._clean_email)
        self.assertEqual(form.initial['email'], form.previous_email)

        # Verify that the form's save method is protected in templates.
        self.assertTrue(
            hasattr(form.save, 'alters_data')
            or hasattr(form.save, 'do_not_call_in_templates')
        )

    def test_blank_data(self):
        # Empty form is expected to be invalid.
        form = self._init_form(data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'email': ["Enter a valid email address."]})

    def test_invalid_email(self):
        test_data = [
            (
                # Too-long email address is expected to be rejected.
                "a" * self.user._meta.get_field('email').max_length + "@xyz.biz",
                f"Ensure that this value has at most "
                f"{self.user._meta.get_field('email').max_length} characters"
            ),
            # Email address consisting of only whitespace is expected to be rejected.
            (" \t \r \f ", "Enter a valid email address."),
            # Email address containing invalid characters is expected to be rejected.
            ("abc[def]gh@localhost", "Enter a valid email address."),
            ("abc def gh@localhost", "Enter a valid email address."),
            # Email address containing more than one 'at' sign is expected to be rejected.
            ("abc@def@gh@localhost", "Enter a valid email address."),
        ]
        for new_email, expected_error in test_data:
            with self.subTest(value=new_email):
                form = self._init_form(data={'email': new_email}, instance=self.user)
                self.assertFalse(form.is_valid())
                self.assertEqual(len(form.errors['email']), 1)
                self.assertStartsWith(form.errors['email'][0], expected_error)

    def test_valid_strange_email(self):
        test_data = [
            "\"abc@def\"@example.com",
            "user+mailbox@example.com",
            "customer/department=shipping@example.com",
            "$A12345@example.com",
            "!def!xyz%abc@example.com",
        ]
        for new_email in test_data:
            with self.subTest(value=new_email):
                form = self._init_form(data={'email': new_email}, instance=self.user)
                self.assertTrue(form.is_valid(), msg=repr(form.errors))

    def test_invalid_prefix_email(self):
        for obj_tag, obj in (("normal email", self.user),
                             ("invalid email", self.invalid_email_user)):
            transformed_email = f"{settings.INVALID_PREFIX}{obj._clean_email}"
            with self.subTest(tag=obj_tag, value=transformed_email):
                form = self._init_form(data={'email': transformed_email}, instance=self.user)
                self.assertFalse(form.is_valid())
                self.assertEqual(len(form.errors['email']), 1)
                self.assertStartsWith(
                    form.errors['email'][0],
                    f"Email address cannot start with {settings.INVALID_PREFIX}"
                )

    def test_same_email(self):
        # Email address without any change is expected to be accepted.
        form = self._init_form(data={'email': self.user.email}, instance=self.user)
        self.assertTrue(form.is_valid())
        form.save(commit=False)
        # Since no change is done in the address, no email is expected to be sent.
        self.assertEqual(len(mail.outbox), 0)

        form = self._init_form(
            data={'email': self.invalid_email_user._clean_email},
            instance=self.invalid_email_user)
        self.assertTrue(form.is_valid())
        form.save(commit=False)
        # Since no change is done in the address, no email is expected to be sent.
        self.assertEqual(len(mail.outbox), 0)

    def test_case_modified_email(self):
        test_transforms = [
            lambda e: e.capitalize(),
            lambda e: _snake_str(e),
            lambda e: e.upper(),
        ]
        test_data = [
            (obj_tag, obj, tr)
            for obj_tag, obj in (("normal email", self.user),
                                 ("invalid email", self.invalid_email_user))
            for tr in test_transforms
        ]

        for obj_tag, obj, transform in test_data:
            transformed_email = transform(obj._clean_email)
            with self.subTest(tag=obj_tag, value=transformed_email):
                form = self._init_form(data={'email': transformed_email}, instance=obj)
                self.assertTrue(form.is_valid(), msg=repr(form.errors))

    def test_nonunique_email(self):
        normal_email_user = UserFactory()
        test_transforms = [
            lambda e: e,
            lambda e: _snake_str(e),
            lambda e: e.upper(),
        ]
        test_data = [
            (obj_tag, obj, tr)
            for obj_tag, obj in (("normal email", normal_email_user),
                                 ("invalid email", self.invalid_email_user))
            for tr in test_transforms
        ]

        for obj_tag, obj, transform in test_data:
            transformed_email = transform(obj._clean_email)
            with self.subTest(tag=obj_tag, value=transformed_email):
                form = self._init_form(data={'email': transformed_email}, instance=self.user)
                self.assertFalse(form.is_valid())
                self.assertEqual(form.errors, {'email': ["User address already in use."]})

        # Attempting to use an email address similar to an existing invalid address
        # is expected to result in error.
        form = self._init_form(
            data={'email': self.invalid_email_user.email},
            instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertTrue(
            any(
                e.startswith(f"Email address cannot start with {settings.INVALID_PREFIX}")
                for e in form.errors['email']
            ),
            msg=repr(form.errors))
        self.assertNotIn("User address already in use.", form.errors['email'])

        transformed_email = "{}{}".format(
            settings.INVALID_PREFIX, self.invalid_email_user._clean_email)
        transformed_email = _snake_str(transformed_email.lower())
        form = self._init_form(data={'email': transformed_email}, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['email'], ["User address already in use."])

    def test_valid_data(self):
        for obj_tag, obj in (("normal email", self.user),
                             ("invalid email", self.invalid_email_user)):
            with self.subTest(tag=obj_tag):
                new_email = f"{obj.username}@{obj.username}.onion"
                form = self._init_form(data={'email': new_email}, instance=obj)
                self.assertTrue(form.is_valid())
                user = form.save(commit=False)
                self.assertEqual(user.pk, obj.pk)
                self.assertEqual(user.email, new_email)

    def test_view_page(self):
        page = self.app.get(reverse('email_update'), user=self.user)
        self.assertEqual(page.status_int, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertIsInstance(page.context['form'], EmailUpdateForm)

    @override_settings(EMAIL_SUBJECT_PREFIX_FULL="TEST ")
    def test_form_submit(self, obj=None):
        obj = self.user if obj is None else obj
        page = self.app.get(reverse('email_update'), user=obj)
        old_email = obj._clean_email
        new_email = '{}@ps.org'.format(_snake_str(obj.username))
        unchanged_email = obj.email

        page.form['email'] = new_email
        page = page.form.submit()
        obj.refresh_from_db()
        self.assertRedirects(
            page,
            reverse('profile_edit', kwargs={
                'pk': obj.profile.pk, 'slug': obj.profile.autoslug})
        )
        self.assertEqual(obj.email, unchanged_email)
        self.assertEqual(len(mail.outbox), 2)
        test_contents = {
            old_email: (
                "you (or someone on your behalf) requested "
                "a change of your email address",
                f"The new address is: {new_email}",
            ),
            new_email: (
                "you requested to change your email address",
                "Please go to the following page to confirm your new email address:",
            ),
        }
        for i, recipient in enumerate([old_email, new_email]):
            self.assertEqual(mail.outbox[i].subject, "TEST Change of email address")
            self.assertEqual(mail.outbox[i].from_email, settings.DEFAULT_FROM_EMAIL)
            self.assertEqual(mail.outbox[i].to, [recipient])
            for content in test_contents[recipient]:
                self.assertIn(content, mail.outbox[i].body)

    def test_form_submit_for_invalid_email(self):
        self.test_form_submit(obj=self.invalid_email_user)


class EmailStaffUpdateFormTests(EmailUpdateFormTests):
    @classmethod
    def setUpTestData(cls):
        cls.supervisor = UserFactory(is_superuser=True, profile=None)
        super().setUpTestData()

    def _init_form(self, data=None, instance=None):
        return EmailStaffUpdateForm(data=data, instance=instance)

    def test_view_page(self):
        page = self.app.get(
            reverse('staff_email_update', kwargs={
                'pk': self.user.profile.pk, 'slug': self.user.profile.autoslug}),
            user=self.supervisor)
        self.assertEqual(page.status_int, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertIsInstance(page.context['form'], EmailStaffUpdateForm)

    def test_form_submit(self, obj=None):
        obj = self.user if obj is None else obj
        page = self.app.get(
            reverse('staff_email_update', kwargs={
                'pk': obj.profile.pk, 'slug': obj.profile.autoslug}),
            user=self.supervisor)
        new_email = '{}@ps.org'.format(_snake_str(obj.username))
        page.form['email'] = new_email
        page = page.form.submit()
        obj.refresh_from_db()
        self.assertRedirects(
            page,
            reverse('profile_edit', kwargs={
                'pk': obj.profile.pk, 'slug': obj.profile.autoslug})
        )
        self.assertEqual(obj.email, new_email)
        self.assertEqual(len(mail.outbox), 0)
