import re
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.views import INTERNAL_RESET_SESSION_TOKEN
from django.contrib.sessions.backends.cache import SessionStore
from django.core import mail
from django.http import HttpRequest
from django.test import override_settings, tag
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django_webtest import WebTest
from faker import Faker

from core.auth import auth_log
from core.forms import (
    EmailStaffUpdateForm,
    EmailUpdateForm,
    SystemPasswordChangeForm,
    SystemPasswordResetForm,
    SystemPasswordResetRequestForm,
    UserAuthenticationForm,
    UsernameRemindRequestForm,
    UsernameUpdateForm,
    UserRegistrationForm,
)
from core.views import PasswordResetConfirmView, PasswordResetView, UsernameRemindView

from ..assertions import AdditionalAsserts
from ..factories import UserFactory


def _snake_str(string):
    return "".join([c if i % 2 else c.upper() for i, c in enumerate(string)])


@tag("forms", "forms-auth")
@override_settings(LANGUAGE_CODE="en")
class UserRegistrationFormTests(AdditionalAsserts, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.expected_fields = [
            "email",
            "password1",
            "password2",
            "username",
            "realm",
        ]
        cls.honeypot_field = "realm"
        cls.user_one = UserFactory(invalid_email=True)
        cls.user_two = UserFactory(is_active=False)
        cls.test_transforms = [
            lambda v: v,
            lambda v: v.upper(),
            lambda v: _snake_str(v),
        ]
        cls.faker = Faker()

    def test_init(self):
        form_empty = UserRegistrationForm()

        # Verify that the expected fields are part of the form.
        self.assertEqual(set(self.expected_fields), set(form_empty.fields))

        # Verify that 'previous' values are empty.
        self.assertEqual(form_empty.previous_uname, "")
        self.assertEqual(form_empty.previous_email, "")

        # Verify that only neccesary fields are marked 'required'.
        for field in self.expected_fields:
            with self.subTest(field=field):
                if field != self.honeypot_field:
                    self.assertTrue(form_empty.fields[field].required)
                else:
                    self.assertFalse(form_empty.fields[field].required)

        # Verify that the form's save method is protected in templates.
        self.assertTrue(hasattr(form_empty.save, "alters_data"))

    @patch("core.mixins.is_password_compromised")
    def test_blank_data(self, mock_pwd_check):
        # Empty form is expected to be invalid.
        form = UserRegistrationForm(data={})
        mock_pwd_check.side_effect = AssertionError(
            "password check API was unexpectedly called"
        )
        self.assertFalse(form.is_valid())
        for field in set(self.expected_fields) - set([self.honeypot_field]):
            with self.subTest(field=field):
                self.assertIn(field, form.errors)

    @patch("core.mixins.is_password_compromised")
    def test_nonunique_username(self, mock_pwd_check):
        mock_pwd_check.return_value = (False, 0)
        for transform in self.test_transforms:
            transformed_uname = transform(self.user_two.username)
            with self.subTest(value=transformed_uname):
                pwd = self.faker.password()
                form = UserRegistrationForm(
                    data={
                        "username": transformed_uname,
                        "password1": pwd,
                        "password2": pwd,
                        "email": self.faker.email(),
                    }
                )
                self.assertFalse(form.is_valid())
                self.assertIn("username", form.errors)
                self.assertEqual(
                    form.errors["username"],
                    ["A user with a similar username already exists."],
                )
                self.assertNotIn("password1", form.errors)

    @patch("core.mixins.is_password_compromised")
    def test_nonunique_email(self, mock_pwd_check):
        mock_pwd_check.return_value = (False, 0)
        for transform in self.test_transforms:
            transformed_email = transform(self.user_one._clean_email)
            with self.subTest(value=transformed_email):
                pwd = self.faker.password()
                form = UserRegistrationForm(
                    data={
                        "username": self.faker.user_name(),
                        "password1": pwd,
                        "password2": pwd,
                        "email": transformed_email,
                    }
                )
                self.assertFalse(form.is_valid())
                self.assertIn("email", form.errors)
                self.assertEqual(form.errors["email"], ["User address already in use."])
                self.assertNotIn("password1", form.errors)

    def test_weak_password(self):
        weak_password_tests(
            self,
            "core.mixins.is_password_compromised",
            UserRegistrationForm,
            (),
            {
                "username": self.faker.user_name(),
                "password1": "not very strong",
                "password2": "not very strong",
                "email": self.faker.email(),
            },
            "password1",
        )

    def test_strong_password(self):
        registration_data = {
            "username": self.faker.user_name(),
            "password1": "very strong indeed",
            "password2": "very strong indeed",
            "email": self.faker.email(),
        }
        user = strong_password_tests(
            self,
            "core.mixins.is_password_compromised",
            UserRegistrationForm,
            (),
            registration_data,
        )
        self.assertEqual(user.username, registration_data["username"])
        self.assertEqual(user.email, registration_data["email"])

    @patch("core.mixins.is_password_compromised")
    def test_honeypot(self, mock_pwd_check):
        mock_pwd_check.return_value = (False, 0)
        for expected_result, injected_value in (
            (True, "  \n \f  "),
            (False, self.faker.word()),
        ):
            pwd = self.faker.password()
            form = UserRegistrationForm(
                data={
                    "username": self.faker.user_name(),
                    "password1": pwd,
                    "password2": pwd,
                    "email": self.faker.email(),
                    self.honeypot_field: injected_value,
                }
            )
            if expected_result is True:
                self.assertTrue(form.is_valid())
            if expected_result is False:
                with self.assertLogs("PasportaServo.auth", level="ERROR") as log:
                    self.assertFalse(form.is_valid())
                self.assertIn(self.honeypot_field, form.errors)
                self.assertEqual(form.errors[self.honeypot_field], [""])
                self.assertEqual(len(log.records), 1)
                self.assertEqual(
                    log.records[0].message,
                    "Registration failed, flies found in honeypot.",
                )

    def test_view_page(self):
        page = self.app.get(reverse("register"))
        self.assertEqual(page.status_code, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertIsInstance(page.context["form"], UserRegistrationForm)

    @patch("core.mixins.is_password_compromised")
    def test_form_submit(self, mock_pwd_check):
        page = self.app.get(reverse("register"))
        page.form["username"] = uname = self.faker.user_name()
        page.form["email"] = email = self.faker.email()
        page.form["password1"] = page.form["password2"] = self.faker.password()
        mock_pwd_check.return_value = (False, 0)
        page = page.form.submit()
        mock_pwd_check.assert_called_once()
        self.assertEqual(page.status_code, 302)
        self.assertRedirects(
            page, reverse("profile_create"), fetch_redirect_response=False
        )
        while page.status_code == 302:
            page = page.follow()
        self.assertEqual(page.context["user"].username, uname)
        self.assertEqual(page.context["user"].email, email)


@tag("forms", "forms-auth")
@override_settings(LANGUAGE_CODE="en")
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
            "username",
            "password",
        ]
        # Verify that the expected fields are part of the form.
        self.assertEqual(set(expected_fields), set(form_empty.fields))

    def test_blank_data(self):
        # Empty form is expected to be invalid.
        form = UserAuthenticationForm(data={})
        self.assertFalse(form.is_valid())

        # Form with empty password field is expected to be invalid.
        form = UserAuthenticationForm(data={"username": self.user.username})
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)

        # Form with empty username field is expected to be invalid.
        form = UserAuthenticationForm(data={"password": "adm1n"})
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_inactive_user_login(self):
        self.user.is_active = False
        self.user.save()

        # The error for an inactive user's login with incorrect credentials is
        # expected to be along the lines of 'incorrect username or password'.
        form = UserAuthenticationForm(
            self.dummy_request,
            {"username": self.user.username, "password": "incorrect"},
        )
        self.assertFalse(form.is_valid())
        self.assertStartsWith(
            form.non_field_errors()[0], "Please enter the correct username and password"
        )
        self.assertNotIn("restore_request_id", self.dummy_request.session)

        # The error for an inactive user's login with correct credentials is
        # expected to inform that the account is inactive.  In addition, the
        # restore_request_id is expected in the session and a warning emitted
        # on the authentication log.
        with self.assertLogs("PasportaServo.auth", level="WARNING") as log:
            form = UserAuthenticationForm(
                self.dummy_request,
                {"username": self.user.username, "password": "adm1n"},
            )
            self.assertFalse(form.is_valid())
        self.assertEqual(
            form.non_field_errors()[0], str(form.error_messages["inactive"])
        )
        self.assertIn("restore_request_id", self.dummy_request.session)
        self.assertIs(type(self.dummy_request.session["restore_request_id"]), tuple)
        self.assertEqual(len(self.dummy_request.session["restore_request_id"]), 2)
        self.assertEqual(len(log.records), 1)
        self.assertIn("the account is deactivated", log.output[0])

    def test_active_user_login(self):
        self.assertTrue(self.user.is_active)

        # The error for an active user's login with incorrect credentials is
        # expected to be along the lines of 'incorrect username or password'.
        form = UserAuthenticationForm(
            self.dummy_request,
            {"username": self.user.username, "password": "incorrect"},
        )
        self.assertFalse(form.is_valid())
        self.assertStartsWith(
            form.non_field_errors()[0], "Please enter the correct username and password"
        )
        self.assertNotIn("restore_request_id", self.dummy_request.session)

        # For an active user's login with correct credentials, no error is
        # expected.  In addition, the restore_request_id shall not be in the
        # session.
        form = UserAuthenticationForm(
            self.dummy_request, {"username": self.user.username, "password": "adm1n"}
        )
        self.assertTrue(form.is_valid())
        self.assertNotIn("restore_request_id", self.dummy_request.session)

    def test_case_sensitivity(self):
        # The error for login with username different in case is expected to
        # be along the lines of 'incorrect username or password', and inform
        # that the field is case-sensitive.
        for credentials in (
            (self.user.username.upper(), "incorrect"),
            (self.user.username.upper(), "adm1n"),
        ):
            form = UserAuthenticationForm(
                self.dummy_request,
                {"username": credentials[0], "password": credentials[1]},
            )
            self.assertFalse(form.is_valid())
            self.assertStartsWith(
                form.non_field_errors()[0],
                "Please enter the correct username and password",
            )
            self.assertIn(
                "Note that both fields are case-sensitive", form.non_field_errors()[0]
            )

    def test_view_page(self):
        page = self.app.get(reverse("login"))
        self.assertEqual(page.status_code, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertIsInstance(page.context["form"], UserAuthenticationForm)

    def test_form_submit_invalid_credentials(self):
        page = self.app.get(reverse("login"))
        page.form["username"] = "SomeUser"
        page.form["password"] = ".incorrect."
        page = page.form.submit()
        self.assertEqual(page.status_code, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertGreaterEqual(len(page.context["form"].errors), 1)

    def test_form_submit_valid_credentials(self):
        page = self.app.get(reverse("login"))
        page.form["username"] = self.user.username
        page.form["password"] = "adm1n"
        page = page.form.submit()
        self.assertEqual(page.status_code, 302)
        self.assertRedirects(page, "/")


@tag("forms", "forms-auth")
@override_settings(LANGUAGE_CODE="en")
class UsernameUpdateFormTests(AdditionalAsserts, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def setUp(self):
        self.user.refresh_from_db()

    def test_init(self):
        form = UsernameUpdateForm(instance=self.user)
        # Verify that the expected fields are part of the form.
        self.assertEqual(["username"], list(form.fields))
        # Verify that the form stores the username before a change.
        self.assertTrue(hasattr(form, "previous_uname"))
        self.assertEqual(form.previous_uname, self.user.username)
        # Verify the form's save method is protected in templates.
        self.assertTrue(
            hasattr(form.save, "alters_data")
            or hasattr(form.save, "do_not_call_in_templates")
        )

    def test_blank_data(self):
        # Empty form is expected to be invalid.
        form = UsernameUpdateForm(data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {"username": ["This field is required."]})

    def test_invalid_username(self):
        test_data = [
            (
                # Too-long username is expected to be rejected.
                "a" * (self.user._meta.get_field("username").max_length + 1),
                f"Ensure that this value has at most "
                f"{self.user._meta.get_field('username').max_length} characters",
            ),
            # Username consisting of only whitespace is expected to be rejected.
            (" \t \r \f ", "This field is required"),
            # Usernames containing invalid characters are expected to be rejected.
            (
                self.user.username + " id",
                "Enter a username conforming to these rules: ",
            ),
            (
                self.user.username + "=+~",
                "Enter a username conforming to these rules: ",
            ),
            ("A<B", "Enter a username conforming to these rules: "),
        ]
        for new_username, expected_error in test_data:
            with self.subTest(value=new_username):
                form = UsernameUpdateForm(
                    data={"username": new_username}, instance=self.user
                )
                self.assertFalse(form.is_valid())
                self.assertEqual(len(form.errors["username"]), 1)
                self.assertStartsWith(form.errors["username"][0], expected_error)

    def test_same_username(self):
        # Username without any change is expected to be accepted.
        form = UsernameUpdateForm(
            data={"username": self.user.username}, instance=self.user
        )
        self.assertTrue(form.is_valid())

        UserFactory(username=_snake_str(self.user.username))
        form = UsernameUpdateForm(
            data={"username": self.user.username}, instance=self.user
        )
        self.assertTrue(form.is_valid())

    def test_case_modified_username(self):
        form = UsernameUpdateForm(
            data={"username": self.user.username.capitalize()}, instance=self.user
        )
        self.assertTrue(form.is_valid())
        form = UsernameUpdateForm(
            data={"username": self.user.username.upper()}, instance=self.user
        )
        self.assertTrue(form.is_valid())

    def test_case_modified_nonunique_username(self):
        UserFactory(username=_snake_str(self.user.username))
        UserFactory(username=self.user.username.upper())
        form = UsernameUpdateForm(
            data={"username": self.user.username.capitalize()}, instance=self.user
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors,
            {"username": ["A user with a similar username already exists."]},
        )

    def test_nonunique_username(self):
        other_user = UserFactory()
        for new_username in (
            other_user.username,
            other_user.username.capitalize(),
            _snake_str(other_user.username),
        ):
            with self.subTest(value=new_username):
                form = UsernameUpdateForm(
                    data={"username": new_username}, instance=self.user
                )
                self.assertFalse(form.is_valid())
                self.assertEqual(
                    form.errors,
                    {"username": ["A user with a similar username already exists."]},
                )

    def test_valid_data(self):
        new_username = self.user.username * 2
        form = UsernameUpdateForm(data={"username": new_username}, instance=self.user)
        self.assertTrue(form.is_valid())
        user = form.save(commit=False)
        self.assertEqual(user.pk, self.user.pk)
        self.assertEqual(user.username, new_username)

    def test_view_page(self):
        page = self.app.get(reverse("username_change"), user=self.user)
        self.assertEqual(page.status_code, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertIsInstance(page.context["form"], UsernameUpdateForm)

    def test_form_submit(self):
        page = self.app.get(reverse("username_change"), user=self.user)
        page.form["username"] = new_username = _snake_str(self.user.username)
        page = page.form.submit()
        self.user.refresh_from_db()
        self.assertRedirects(
            page,
            reverse(
                "profile_edit",
                kwargs={"pk": self.user.profile.pk, "slug": self.user.profile.autoslug},
            ),
        )
        self.assertEqual(self.user.username, new_username)


@tag("forms", "forms-auth")
@override_settings(LANGUAGE_CODE="en")
class EmailUpdateFormTests(AdditionalAsserts, WebTest):
    empty_is_invalid = True

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
        self.assertEqual(["email"], list(form.fields))
        # Verify that the form stores the email address before a change.
        self.assertTrue(hasattr(form, "previous_email"))
        self.assertEqual(form.previous_email, self.user.email)
        self.assertEqual(form.initial["email"], form.previous_email)

        form = self._init_form(instance=self.invalid_email_user)
        # Verify that the form stores the cleaned up email address.
        self.assertTrue(hasattr(form, "previous_email"))
        self.assertEqual(form.previous_email, self.invalid_email_user._clean_email)
        self.assertEqual(form.initial["email"], form.previous_email)

        # Verify that the form's save method is protected in templates.
        self.assertTrue(
            hasattr(form.save, "alters_data")
            or hasattr(form.save, "do_not_call_in_templates")
        )

    def test_blank_data(self):
        # Empty form is expected to follow the 'empty_is_invalid' setting.
        form = self._init_form(data={}, instance=self.user)
        if self.empty_is_invalid:
            self.assertFalse(form.is_valid())
            self.assertEqual(form.errors, {"email": ["Enter a valid email address."]})
        else:
            self.assertTrue(form.is_valid(), msg=repr(form.errors))

    def test_invalid_email(self):
        test_data = [
            (
                # Too-long email address is expected to be rejected.
                "a" * self.user._meta.get_field("email").max_length + "@xyz.biz",
                f"Ensure that this value has at most "
                f"{self.user._meta.get_field('email').max_length} characters",
            ),
            # Email address containing invalid characters is expected to be rejected.
            ("abc[def]gh@localhost", "Enter a valid email address."),
            ("abc def gh@localhost", "Enter a valid email address."),
            # Email address containing more than one 'at' sign is expected to be rejected.
            ("abc@def@gh@localhost", "Enter a valid email address."),
        ]
        if self.empty_is_invalid:
            test_data.append(
                # Email address consisting of only whitespace is expected to be rejected.
                (" \t \r \f ", "Enter a valid email address.")
            )
        for new_email, expected_error in test_data:
            with self.subTest(value=new_email):
                form = self._init_form(data={"email": new_email}, instance=self.user)
                self.assertFalse(form.is_valid())
                self.assertEqual(len(form.errors["email"]), 1)
                self.assertStartsWith(form.errors["email"][0], expected_error)

    def test_valid_strange_email(self):
        test_data = [
            '"abc@def"@example.com',
            "user+mailbox@example.com",
            "customer/department=shipping@example.com",
            "$A12345@example.com",
            "!def!xyz%abc@example.com",
        ]
        for new_email in test_data:
            with self.subTest(value=new_email):
                form = self._init_form(data={"email": new_email}, instance=self.user)
                self.assertTrue(form.is_valid(), msg=repr(form.errors))

    def test_invalid_prefix_email(self):
        for obj_tag, obj in (
            ("normal email", self.user),
            ("invalid email", self.invalid_email_user),
        ):
            transformed_email = f"{settings.INVALID_PREFIX}{obj._clean_email}"
            with self.subTest(tag=obj_tag, value=transformed_email):
                form = self._init_form(
                    data={"email": transformed_email}, instance=self.user
                )
                self.assertFalse(form.is_valid())
                self.assertEqual(len(form.errors["email"]), 1)
                self.assertStartsWith(
                    form.errors["email"][0],
                    f"Email address cannot start with {settings.INVALID_PREFIX}",
                )

    def test_same_email(self):
        # Email address without any change is expected to be accepted.
        form = self._init_form(data={"email": self.user.email}, instance=self.user)
        self.assertTrue(form.is_valid())
        form.save(commit=False)
        # Since no change is done in the address, no email is expected to be sent.
        self.assertEqual(len(mail.outbox), 0)

        form = self._init_form(
            data={"email": self.invalid_email_user._clean_email},
            instance=self.invalid_email_user,
        )
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
            for obj_tag, obj in (
                ("normal email", self.user),
                ("invalid email", self.invalid_email_user),
            )
            for tr in test_transforms
        ]

        for obj_tag, obj, transform in test_data:
            transformed_email = transform(obj._clean_email)
            with self.subTest(tag=obj_tag, value=transformed_email):
                form = self._init_form(data={"email": transformed_email}, instance=obj)
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
            for obj_tag, obj in (
                ("normal email", normal_email_user),
                ("invalid email", self.invalid_email_user),
            )
            for tr in test_transforms
        ]

        for obj_tag, obj, transform in test_data:
            transformed_email = transform(obj._clean_email)
            with self.subTest(tag=obj_tag, value=transformed_email):
                form = self._init_form(
                    data={"email": transformed_email}, instance=self.user
                )
                self.assertFalse(form.is_valid())
                self.assertEqual(
                    form.errors, {"email": ["User address already in use."]}
                )

        # Attempting to use an email address similar to an existing invalid address
        # is expected to result in error.
        form = self._init_form(
            data={"email": self.invalid_email_user.email}, instance=self.user
        )
        self.assertFalse(form.is_valid())
        self.assertTrue(
            any(
                e.startswith(
                    f"Email address cannot start with {settings.INVALID_PREFIX}"
                )
                for e in form.errors["email"]
            ),
            msg=repr(form.errors),
        )
        self.assertNotIn("User address already in use.", form.errors["email"])

        transformed_email = "{}{}".format(
            settings.INVALID_PREFIX, self.invalid_email_user._clean_email
        )
        transformed_email = _snake_str(transformed_email.lower())
        form = self._init_form(data={"email": transformed_email}, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors["email"], ["User address already in use."])

    def test_valid_data(self):
        for obj_tag, obj in (
            ("normal email", self.user),
            ("invalid email", self.invalid_email_user),
        ):
            with self.subTest(tag=obj_tag):
                new_email = f"{obj.username}@{obj.username}.onion"
                form = self._init_form(data={"email": new_email}, instance=obj)
                self.assertTrue(form.is_valid())
                user = form.save(commit=False)
                self.assertEqual(user.pk, obj.pk)
                self.assertEqual(user.email, new_email)

    def test_view_page(self):
        page = self.app.get(reverse("email_update"), user=self.user)
        self.assertEqual(page.status_code, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertIsInstance(page.context["form"], EmailUpdateForm)

    @override_settings(EMAIL_SUBJECT_PREFIX_FULL="TEST ")
    def test_form_submit(self, obj=None):
        obj = self.user if obj is None else obj
        page = self.app.get(reverse("email_update"), user=obj)
        old_email = obj._clean_email
        new_email = "{}@ps.org".format(_snake_str(obj.username))
        unchanged_email = obj.email

        page.form["email"] = new_email
        page = page.form.submit()
        obj.refresh_from_db()
        self.assertRedirects(
            page,
            reverse(
                "profile_edit",
                kwargs={"pk": obj.profile.pk, "slug": obj.profile.autoslug},
            ),
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
            reverse(
                "staff_email_update",
                kwargs={"pk": self.user.profile.pk, "slug": self.user.profile.autoslug},
            ),
            user=self.supervisor,
        )
        self.assertEqual(page.status_code, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertIsInstance(page.context["form"], EmailStaffUpdateForm)

    def test_form_submit(self, obj=None):
        obj = self.user if obj is None else obj
        page = self.app.get(
            reverse(
                "staff_email_update",
                kwargs={"pk": obj.profile.pk, "slug": obj.profile.autoslug},
            ),
            user=self.supervisor,
        )
        new_email = "{}@ps.org".format(_snake_str(obj.username))
        page.form["email"] = new_email
        page = page.form.submit()
        obj.refresh_from_db()
        self.assertRedirects(
            page,
            reverse(
                "profile_edit",
                kwargs={"pk": obj.profile.pk, "slug": obj.profile.autoslug},
            ),
        )
        self.assertEqual(obj.email, new_email)
        self.assertEqual(len(mail.outbox), 0)


@tag("forms", "forms-auth")
@override_settings(LANGUAGE_CODE="en")
class SystemPasswordResetRequestFormTests(AdditionalAsserts, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.active_user = UserFactory()
        cls.inactive_user = UserFactory(is_active=False)
        cls.active_invalid_email_user = UserFactory(invalid_email=True)
        cls.inactive_invalid_email_user = UserFactory(
            invalid_email=True, is_active=False
        )
        cls.view_page_url = reverse("password_reset")
        cls.view_page_success_url = reverse("password_reset_done")

    def _init_form(self, data=None):
        return SystemPasswordResetRequestForm(data=data)

    @property
    def _related_view(self):
        return PasswordResetView

    def test_init(self):
        form = self._init_form()
        # Verify that the expected fields are part of the form.
        self.assertEqual(["email"], list(form.fields))
        # Verify that the form's save method is protected in templates.
        self.assertTrue(
            hasattr(form.save, "alters_data")
            or hasattr(form.save, "do_not_call_in_templates")
        )

    def test_blank_data(self):
        # Empty form is expected to be invalid.
        form = self._init_form(data={})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {"email": ["This field is required."]})

    def test_get_users(self):
        with self.settings(
            PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]
        ):
            active_md5_user1 = UserFactory()
        with self.settings(
            PASSWORD_HASHERS=["django.contrib.auth.hashers.UnsaltedMD5PasswordHasher"]
        ):
            active_md5_user2 = UserFactory(invalid_email=True)
        form = self._init_form()

        # All types of users with useable passwords are expected to be returned.
        for user, expected_empty in [
            (self.active_user, True),
            (self.inactive_user, True),
            (self.active_invalid_email_user, False),
            (self.inactive_invalid_email_user, False),
            (active_md5_user1, True),
            (active_md5_user2, False),
        ]:
            with self.subTest(email=user.email, active=user.is_active):
                got_users = list(form.get_users(user._clean_email))
                self.assertEqual(got_users, [user])
                self.assertEqual(got_users[0].email, user._clean_email)
                got_users = list(
                    form.get_users(f"{settings.INVALID_PREFIX}{user._clean_email}")
                )
                self.assertEqual(got_users, [] if expected_empty else [user])
                if not expected_empty:
                    self.assertEqual(got_users[0].email, user._clean_email)

        # Users with unuseable passwords are expected to be not returned.
        active_nonepwd_user = UserFactory()
        active_nonepwd_user.set_unusable_password()
        active_nonepwd_user.save()
        inactive_nonepwd_user = UserFactory(is_active=False)
        inactive_nonepwd_user.set_unusable_password()
        inactive_nonepwd_user.save()
        for user in [active_nonepwd_user, inactive_nonepwd_user]:
            with self.subTest(email=user.email, pwd=None, active=user.is_active):
                got_users = list(form.get_users(user._clean_email))
                self.assertEqual(got_users, [])

    def _get_admin_message(self, user):
        return (
            f"User '{user.username}' tried to reset the login password,"
            " but the account is deactivated"
        )

    def _get_email_content(self, active):
        test_data = {}
        test_data[True] = (
            "TEST Password reset",
            [
                "You're receiving this email because you requested "
                "a password reset for your user account",
                "Please go to the following page and choose a new password:",
            ],
            [
                "you deactivated your account previously",
            ],
        )
        test_data[False] = (
            "TEST Password reset",
            [
                "You're receiving this email because you requested "
                "a password reset for your user account",
                "Unfortunately, you deactivated your account previously, "
                "and first it needs to be re-activated",
            ],
            [
                "Please go to the following page and choose a new password:",
            ],
        )
        return test_data[active]

    @override_settings(EMAIL_SUBJECT_PREFIX_FULL="TEST ")
    def test_active_user_request(self):
        # Active users are expected to receive an email with password reset link.
        for user_tag, user in [
            ("normal email", self.active_user),
            ("invalid email", self.active_invalid_email_user),
        ]:
            with self.subTest(tag=user_tag):
                # No warnings are expected on the auth log.
                with self.assertLogs("PasportaServo.auth", level="WARNING") as log:
                    form = self._init_form({"email": user._clean_email})
                    self.assertTrue(form.is_valid())
                    form.save(
                        subject_template_name=self._related_view.subject_template_name,
                        email_template_name=self._related_view.email_template_name,
                        html_email_template_name=self._related_view.html_email_template_name,
                    )
                    # Workaround for lack of assertNotLogs.
                    auth_log.warning("No warning emitted.")
                self.assertEqual(len(log.records), 1)
                self.assertEqual(log.records[0].message, "No warning emitted.")
                # The email message is expected to describe the password reset procedure.
                title, expected_content, not_expected_content = self._get_email_content(
                    True
                )
                self.assertEqual(len(mail.outbox), 1)
                self.assertEqual(mail.outbox[0].subject, title)
                self.assertEqual(mail.outbox[0].from_email, settings.DEFAULT_FROM_EMAIL)
                self.assertEqual(mail.outbox[0].to, [user._clean_email])
                for content in expected_content:
                    self.assertIn(content, mail.outbox[0].body)
                for content in not_expected_content:
                    self.assertNotIn(content, mail.outbox[0].body)
            mail.outbox = []

    @override_settings(EMAIL_SUBJECT_PREFIX_FULL="TEST ")
    def test_inactive_user_request(self):
        # Inactive users are expected to receive an email with instructions
        # for activating their account and not password reset link.
        for user_tag, user in [
            ("normal email", self.inactive_user),
            ("invalid email", self.inactive_invalid_email_user),
        ]:
            with self.subTest(tag=user_tag):
                # A warning about a deactivated account is expected on the auth log.
                with self.assertLogs("PasportaServo.auth", level="WARNING") as log:
                    form = self._init_form({"email": user._clean_email})
                    self.assertTrue(form.is_valid())
                    form.save(
                        subject_template_name=self._related_view.subject_template_name,
                        email_template_name=self._related_view.email_template_name,
                        html_email_template_name=self._related_view.html_email_template_name,
                    )
                self.assertEqual(len(log.records), 1)
                self.assertStartsWith(
                    log.records[0].message, self._get_admin_message(user)
                )
                # The warning is expected to include a reference number.
                code = re.search(r"\[([A-F0-9-]+)\]", log.records[0].message)
                self.assertIsNotNone(code)
                code = code.group(1)
                # The email message is expected to describe the account reactivation procedure.
                title, expected_content, not_expected_content = self._get_email_content(
                    False
                )
                self.assertEqual(len(mail.outbox), 1)
                self.assertEqual(mail.outbox[0].subject, title)
                self.assertEqual(mail.outbox[0].from_email, settings.DEFAULT_FROM_EMAIL)
                self.assertEqual(mail.outbox[0].to, [user._clean_email])
                for content in expected_content:
                    self.assertIn(content, mail.outbox[0].body)
                for content in not_expected_content:
                    self.assertNotIn(content, mail.outbox[0].body)
                # The email message is expected to include the reference number.
                self.assertIn(code, mail.outbox[0].body)
            mail.outbox = []

    def test_view_page(self):
        page = self.app.get(self.view_page_url)
        self.assertEqual(page.status_code, 200)
        self.assertEqual(len(page.forms), 1)
        self.assertIsInstance(page.context["form"], self._init_form().__class__)

    def test_form_submit(self):
        for user in [
            self.active_user,
            self.active_invalid_email_user,
            self.inactive_user,
            self.inactive_invalid_email_user,
        ]:
            with self.subTest(email=user.email, active=user.is_active):
                page = self.app.get(self.view_page_url)
                page.form["email"] = user.email
                page = page.form.submit()
                self.assertEqual(page.status_code, 302)
                self.assertRedirects(page, self.view_page_success_url)


class UsernameRemindRequestFormTests(SystemPasswordResetRequestFormTests):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.view_page_url = reverse("username_remind")
        cls.view_page_success_url = reverse("username_remind_done")

    def _init_form(self, data=None):
        return UsernameRemindRequestForm(data=data)

    @property
    def _related_view(self):
        return UsernameRemindView

    def _get_admin_message(self, user):
        return (
            f"User '{user.username}' requested a reminder of the username,"
            " but the account is deactivated"
        )

    def _get_email_content(self, active):
        test_data = {}
        test_data[True] = (
            "TEST Username reminder",
            [
                "Your username, in case you've forgotten:",
            ],
            [
                "you deactivated your account previously",
            ],
        )
        test_data[False] = (
            "TEST Username reminder",
            [
                "Your username, in case you've forgotten:",
                "Unfortunately, you deactivated your account previously, "
                "and first it needs to be re-activated",
            ],
            [],
        )
        return test_data[active]


@tag("forms", "forms-auth", "forms-pwd")
@override_settings(LANGUAGE_CODE="en")
class SystemPasswordResetFormTests(AdditionalAsserts, WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(invalid_email=True)
        cls.user.profile.email = cls.user.email
        cls.user.profile.save(update_fields=["email"])
        cls.form_class = SystemPasswordResetForm
        cls.expected_fields = [
            "new_password1",
            "new_password2",
        ]

    def test_init(self):
        form_empty = self.form_class(self.user)
        # Verify that the expected fields are part of the form.
        self.assertEqual(set(self.expected_fields), set(form_empty.fields))
        # Verify that the form's save method is protected in templates.
        self.assertTrue(hasattr(form_empty.save, "alters_data"))

    @patch("core.mixins.is_password_compromised")
    def test_blank_data(self, mock_pwd_check):
        # Empty form is expected to be invalid.
        form = self.form_class(self.user, data={})
        mock_pwd_check.side_effect = AssertionError(
            "password check API was unexpectedly called"
        )
        self.assertFalse(form.is_valid())
        for field in self.expected_fields:
            with self.subTest(field=field):
                self.assertIn(field, form.errors)

    def test_weak_password(self):
        weak_password_tests(
            self,
            "core.mixins.is_password_compromised",
            self.form_class,
            (self.user,),
            {field_name: "adm1n" for field_name in self.expected_fields},
            "new_password1",
        )

    def test_strong_password(self):
        user = strong_password_tests(
            self,
            "core.mixins.is_password_compromised",
            self.form_class,
            (self.user,),
            {field_name: "adm1n" for field_name in self.expected_fields},
        )
        self.assertEqual(user.pk, self.user.pk)

    @patch("django.contrib.auth.views.default_token_generator.check_token")
    def test_view_page(self, mock_check_token):
        mock_check_token.return_value = True
        user_id = urlsafe_base64_encode(force_bytes(self.user.pk))
        page = self.app.get(
            reverse(
                "password_reset_confirm",
                kwargs={
                    "uidb64": user_id if isinstance(user_id, str) else user_id.decode(),
                    "token": PasswordResetConfirmView.reset_url_token,
                },
            )
        )
        self.assertEqual(page.status_code, 200, msg=repr(page))
        self.assertEqual(len(page.forms), 1)
        self.assertIsInstance(page.context["form"], SystemPasswordResetForm)

    @patch("core.mixins.is_password_compromised")
    @patch("django.contrib.auth.views.default_token_generator.check_token")
    def test_form_submit(self, mock_check_token, mock_pwd_check):
        mock_check_token.return_value = True  # Bypass Django's token verification.
        user_id = urlsafe_base64_encode(force_bytes(self.user.pk))
        page = self.app.get(
            reverse(
                "password_reset_confirm",
                kwargs={
                    "uidb64": user_id if isinstance(user_id, str) else user_id.decode(),
                    "token": PasswordResetConfirmView.reset_url_token,
                },
            ),
            user=self.user,
        )
        page.form["new_password1"] = page.form["new_password2"] = Faker().password()
        session = self.app.session
        session[INTERNAL_RESET_SESSION_TOKEN] = None
        session.save()
        mock_pwd_check.return_value = (False, 0)  # Treat password as a strong one.
        self.assertEqual(self.user.email, self.user.profile.email)
        self.assertStartsWith(self.user.email, settings.INVALID_PREFIX)
        page = page.form.submit()
        mock_pwd_check.assert_called_once()
        self.assertEqual(page.status_code, 302, msg=repr(page))
        self.assertRedirects(page, reverse("password_reset_complete"))
        # The marked invalid email address is expected to be marked valid
        # after submission of the form.
        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.email, self.user.profile.email)
        self.assertFalse(self.user.email.startswith(settings.INVALID_PREFIX))


class SystemPasswordChangeFormTests(SystemPasswordResetFormTests):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.form_class = SystemPasswordChangeForm
        cls.expected_fields = [
            "new_password1",
            "new_password2",
            "old_password",
        ]

    def test_view_page(self):
        page = self.app.get(reverse("password_change"), user=self.user)
        self.assertEqual(page.status_code, 200, msg=repr(page))
        self.assertEqual(len(page.forms), 1)
        self.assertIsInstance(page.context["form"], SystemPasswordChangeForm)

    @patch("core.mixins.is_password_compromised")
    def test_form_submit(self, mock_pwd_check):
        page = self.app.get(reverse("password_change"), user=self.user)
        page.form["old_password"] = "adm1n"
        page.form["new_password1"] = "Strong & Courageous"
        page.form["new_password2"] = "Strong & Courageous"
        mock_pwd_check.return_value = (False, 0)  # Treat password as a strong one.
        page = page.form.submit()
        mock_pwd_check.assert_called_once()
        self.assertEqual(page.status_code, 302, msg=repr(page))
        self.assertRedirects(page, reverse("password_change_done"))


def weak_password_tests(
    test_inst, where_to_patch, form_class, form_args, form_data, inspect_field
):
    test_data = [
        (1, True, ""),
        (
            2,
            False,
            "The password selected by you is not very secure. "
            "Such combination of characters is known to cyber-criminals.",
        ),
        (
            100,
            False,
            "The password selected by you is too insecure. "
            "Such combination of characters is very well-known to cyber-criminals.",
        ),
    ]
    for number_seen, expected_result, expected_error in test_data:
        # Mock the response of the Pwned Pwds API to indicate a compromised password,
        # seen a specific number of times.
        with patch(where_to_patch) as mock_pwd_check:
            mock_pwd_check.return_value = (True, number_seen)
            form = form_class(*form_args, data=form_data)
            with test_inst.assertLogs("PasportaServo.auth", level="WARNING") as log:
                test_inst.assertIs(
                    form.is_valid(), expected_result, msg=repr(form.errors)
                )
            mock_pwd_check.assert_called_once_with(form_data[inspect_field])
        if expected_result is False:
            test_inst.assertIn(inspect_field, form.errors)
            test_inst.assertEqual(
                form.errors[inspect_field], ["Choose a less easily guessable password."]
            )
            test_inst.assertEqual(form.non_field_errors(), [expected_error])
        test_inst.assertEqual(
            log.records[0].message,
            f"Password with HIBP count {number_seen} selected in {form_class.__name__}.",
        )


def strong_password_tests(test_inst, where_to_patch, form_class, form_args, form_data):
    # Mock the response of the Pwned Pwds API to indicate non-compromised password.
    with patch(where_to_patch) as mock_pwd_check:
        mock_pwd_check.return_value = (False, 0)
        form = form_class(*form_args, data=form_data)
        test_inst.assertTrue(form.is_valid(), msg=repr(form.errors))
        mock_pwd_check.assert_called_once()
    return form.save(commit=False)
