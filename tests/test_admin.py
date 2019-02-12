from django.urls import reverse

from django_webtest import WebTest

from .factories import AdminUserFactory, StaffUserFactory, UserFactory


class BasicAdminTests(WebTest):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("admin:index")

    def test_admin_logged_out(self):
        response = self.app.get(self.url, status=302)
        self.assertEqual(
            response.location, "{}?next={}".format(reverse("admin:login"), self.url)
        )

    def test_admin_regular_user_logged_in(self):
        user = UserFactory()
        response = self.app.get(self.url, user=user, status=302)
        self.assertEqual(
            response.location, "{}?next={}".format(reverse("admin:login"), self.url)
        )

    def test_admin_staff_user_logged_in(self):
        self.app.get(self.url, user=StaffUserFactory(), status=200)

    def test_admin_admin_user_logged_in(self):
        self.app.get(self.url, user=AdminUserFactory(), status=200)
