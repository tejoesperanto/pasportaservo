from django.test import override_settings
from django.urls import reverse

from django_webtest import WebTest

from .factories import ProfileFactory, UserFactory


class HomeTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("home")

    def test_home(self):
        self.app.get(self.url, status=200)

    @override_settings(LANGUAGE_CODE='en')
    def test_home_logged_in(self):
        user = UserFactory()
        response = self.app.get(self.url, user=user, status=200)
        # self.assertIn(user.username, response.pyquery(".links").text())
        self.assertIn("log out", response.pyquery("header .navigator .nav-session").text())


class BasicProfileTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("profile_redirect")

    def test_profile_redirect(self):
        response = self.app.get(self.url, status=302)
        self.assertEqual(response.location, "/ensaluti/?ps_m=/profilo/")

    def test_profile_too_young(self):
        profile = ProfileFactory(birth_date="2018-01-01")
        response = self.app.get(self.url, user=profile.user, expect_errors=True)
        self.assertEqual(response.status_code, 403)
        self.assertIn("tro juna", response.pyquery("#subtitle").text())

    def test_profile_edit(self):
        profile = ProfileFactory()
        response = self.app.get(self.url, user=profile.user)
        self.assertEqual(response.location, profile.get_edit_url())
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.follow().status_code, 200)
